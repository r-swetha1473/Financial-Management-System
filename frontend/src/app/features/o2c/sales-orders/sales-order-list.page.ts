import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
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
import { Customer, Quotation, SalesOrder } from '../models/o2c.model';
import { O2cApiService } from '../services/o2c-api.service';

@Component({
  selector: 'app-sales-order-list-page',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    PageHeaderComponent,
    O2cBannerComponent,
    FilterBarComponent,
    StatusBadgeComponent,
    PaginationComponent,
    ModalComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
    InrPipe,
  ],
  templateUrl: './sales-order-list.page.html',
})
export class SalesOrderListPage implements OnInit {
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
  items: SalesOrder[] = [];
  customers: Customer[] = [];
  quotations: Quotation[] = [];
  total = 0;
  page = 1;
  readonly pageSize = 20;
  search = '';
  status = '';
  customerId = '';
  editing: SalesOrder | null = null;

  readonly form = this.fb.nonNullable.group({
    orderNumber: ['', Validators.required],
    customerId: ['', Validators.required],
    quotationId: [''],
    orderDate: [new Date().toISOString().slice(0, 10), Validators.required],
    totalAmount: ['0.00', Validators.required],
    status: ['confirmed' as SalesOrder['status'], Validators.required],
  });

  ngOnInit(): void {
    const params = this.route.snapshot.queryParamMap;
    this.customerId = params.get('customerId') ?? '';
    this.api.listCustomers({ pageSize: 100 }).subscribe((result) => (this.customers = result.items));
    this.api.listQuotations({ pageSize: 100 }).subscribe((result) => {
      this.quotations = result.items;
      if (params.get('create') === '1' && this.canEdit()) {
        this.openCreate();
        const quotationId = params.get('quotationId') ?? '';
        const quote = this.quotations.find((row) => row.id === quotationId);
        this.form.patchValue({
          customerId: params.get('customerId') ?? quote?.customerId ?? '',
          quotationId,
          totalAmount: quote?.totalAmount ?? '0.00',
          status: 'confirmed',
        });
      }
    });
    this.load();
    this.form.controls.quotationId.valueChanges.subscribe((quotationId) => {
      const quote = this.quotations.find((row) => row.id === quotationId);
      if (quote) {
        this.form.patchValue({ customerId: quote.customerId, totalAmount: quote.totalAmount }, { emitEvent: false });
      }
    });
  }

  load(): void {
    this.loading.set(true);
    this.api
      .listSalesOrders({ page: this.page, pageSize: this.pageSize, customerId: this.customerId, status: this.status, search: this.search })
      .subscribe({
        next: (result) => {
          this.items = result.items;
          this.total = result.total;
          this.loading.set(false);
        },
        error: () => {
          this.loading.set(false);
          this.error.set('Unable to load sales orders.');
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
          { value: 'confirmed', label: 'Confirmed' },
          { value: 'fulfilled', label: 'Fulfilled' },
          { value: 'cancelled', label: 'Cancelled' },
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
      orderNumber: `SO-${new Date().getFullYear()}-${String(this.total + 1).padStart(3, '0')}`,
      customerId: this.customerId,
      quotationId: '',
      orderDate: new Date().toISOString().slice(0, 10),
      totalAmount: '0.00',
      status: 'confirmed',
    });
    this.modalOpen.set(true);
  }

  openEdit(row: SalesOrder): void {
    this.editing = row;
    this.form.patchValue({
      orderNumber: row.orderNumber,
      customerId: row.customerId,
      quotationId: row.quotationId ?? '',
      orderDate: row.orderDate,
      totalAmount: row.totalAmount,
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
      .saveSalesOrder({
        id: this.editing?.id,
        orderNumber: value.orderNumber,
        customerId: value.customerId,
        quotationId: value.quotationId || null,
        orderDate: value.orderDate,
        totalAmount: parseMoneyInput(value.totalAmount),
        status: value.status,
      })
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.modalOpen.set(false);
          this.toast.success(this.editing ? 'Sales order updated' : 'Sales order created');
          this.load();
        },
        error: (err) => {
          this.saving.set(false);
          this.toast.error('Save failed', err.message);
        },
      });
  }
}
