import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { parseMoneyInput } from '../../../core/utils/money.util';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { FilterBarComponent, FilterBarSelect, FilterBarState } from '../../../shared/components/filter-bar/filter-bar.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { O2cBannerComponent } from '../components/o2c-banner.component';
import { Customer, Quotation } from '../models/o2c.model';
import { O2cApiService } from '../services/o2c-api.service';

@Component({
  selector: 'app-quotation-list-page',
  standalone: true,
  imports: [FormsModule, ReactiveFormsModule, RouterLink, PageHeaderComponent, O2cBannerComponent, FilterBarComponent, StatusBadgeComponent, PaginationComponent, ModalComponent, EmptyStateComponent, LoadingSkeletonComponent, InrPipe],
  templateUrl: './quotation-list.page.html',
})
export class QuotationListPage implements OnInit {
  private readonly api = inject(O2cApiService);
  private readonly toast = inject(ToastService);
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  readonly loading = signal(true);
  readonly error = signal('');
  readonly modalOpen = signal(false);
  readonly saving = signal(false);
  items: Quotation[] = [];
  customers: Customer[] = [];
  total = 0;
  page = 1;
  readonly pageSize = 20;
  search = '';
  status = '';
  customerId = '';
  editing: Quotation | null = null;
  readonly form = this.fb.nonNullable.group({
    quoteNumber: ['', Validators.required],
    customerId: ['', Validators.required],
    quoteDate: [new Date().toISOString().slice(0, 10), Validators.required],
    validUntil: [''],
    totalAmount: ['0.00', Validators.required],
    planDuration: [30],
    billingCycle: ['monthly' as NonNullable<Quotation['billingCycle']>],
    depositAmount: ['0.00'],
    status: ['draft' as Quotation['status'], Validators.required],
  });

  ngOnInit(): void {
    this.api.listCustomers({ pageSize: 100 }).subscribe((result) => (this.customers = result.items));
    this.customerId = this.route.snapshot.queryParamMap.get('customerId') ?? '';
    this.load();
    if (this.route.snapshot.queryParamMap.get('create') === '1' && this.canEdit()) {
      this.openCreate();
      this.form.patchValue({ customerId: this.customerId });
    }
  }

  load(): void {
    this.loading.set(true);
    this.api.listQuotations({ page: this.page, pageSize: this.pageSize, customerId: this.customerId, status: this.status, search: this.search }).subscribe({
      next: (result) => {
        this.items = result.items;
        this.total = result.total;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load subscribed plans.');
      },
    });
  }

  get filterSelects(): FilterBarSelect[] {
    return [
      {
        key: 'customer',
        label: 'Customer',
        blankLabel: 'All customers',
        value: this.customerId,
        options: this.customers.map((customer) => ({ value: customer.id, label: customer.name })),
      },
      {
        key: 'status',
        label: 'Status',
        blankLabel: 'All statuses',
        value: this.status,
        options: [
          { value: 'draft', label: 'Draft' },
          { value: 'sent', label: 'Sent' },
          { value: 'accepted', label: 'Accepted' },
          { value: 'rejected', label: 'Rejected' },
          { value: 'converted', label: 'Converted' },
        ],
      },
    ];
  }

  onFilters(state: FilterBarState): void {
    this.search = state.search;
    this.customerId = state.values['customer'] ?? '';
    this.status = state.values['status'] ?? '';
    this.page = 1;
    this.load();
  }

  openCreate(): void {
    this.editing = null;
    this.form.reset({
      quoteNumber: `Q-${new Date().getFullYear()}-${String(this.total + 1).padStart(3, '0')}`,
      customerId: this.customerId,
      quoteDate: new Date().toISOString().slice(0, 10),
      validUntil: '',
      totalAmount: '0.00',
      planDuration: 30,
      billingCycle: 'monthly',
      depositAmount: '0.00',
      status: 'draft',
    });
    this.modalOpen.set(true);
  }

  openEdit(row: Quotation): void {
    this.editing = row;
    this.form.patchValue({
      quoteNumber: row.quoteNumber,
      customerId: row.customerId,
      quoteDate: row.quoteDate,
      validUntil: row.validUntil ?? '',
      totalAmount: row.totalAmount,
      planDuration: row.planDuration ?? 30,
      billingCycle: row.billingCycle ?? 'monthly',
      depositAmount: row.depositAmount ?? '0.00',
      status: row.status,
    });
    this.modalOpen.set(true);
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    this.saving.set(true);
    this.api
      .saveQuotation({
        id: this.editing?.id,
        quoteNumber: value.quoteNumber,
        customerId: value.customerId,
        quoteDate: value.quoteDate,
        validUntil: value.validUntil || null,
        totalAmount: parseMoneyInput(value.totalAmount),
        planDuration: value.planDuration ? Number(value.planDuration) : null,
        billingCycle: value.billingCycle,
        depositAmount: parseMoneyInput(value.depositAmount),
        status: value.status,
      })
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.modalOpen.set(false);
          this.toast.success(this.editing ? 'Subscribed plan updated' : 'Subscribed plan created');
          this.load();
        },
        error: (err) => {
          this.saving.set(false);
          this.toast.error('Save failed', err.message);
        },
      });
  }

  billingLabel(cycle: Quotation['billingCycle']): string {
    if (cycle === 'one_time') {
      return 'One time';
    }
    if (cycle === 'weekly') {
      return 'Weekly';
    }
    if (cycle === 'monthly') {
      return 'Monthly';
    }
    return '—';
  }
}
