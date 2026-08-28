import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { compareMoney, parseMoneyInput, subtractMoney } from '../../../core/utils/money.util';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog/confirm-dialog.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { FilterBarComponent, FilterBarState } from '../../../shared/components/filter-bar/filter-bar.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { O2cBannerComponent } from '../components/o2c-banner.component';
import { Collection, SalesInvoice } from '../models/o2c.model';
import { O2cApiService } from '../services/o2c-api.service';

@Component({
  selector: 'app-collection-list-page',
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
    ConfirmDialogComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
    InrPipe,
  ],
  templateUrl: './collection-list.page.html',
})
export class CollectionListPage implements OnInit {
  private readonly api = inject(O2cApiService);
  private readonly toast = inject(ToastService);
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);

  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  readonly loading = signal(true);
  readonly error = signal('');
  readonly modalOpen = signal(false);
  readonly confirmOpen = signal(false);
  readonly saving = signal(false);
  items: Collection[] = [];
  invoices: SalesInvoice[] = [];
  total = 0;
  page = 1;
  search = '';
  invoiceAmount = '0.00';
  alreadyPaid = '0.00';
  outstanding = '0.00';
  remainingAfter = '0.00';
  amountError = '';

  readonly form = this.fb.nonNullable.group({
    salesInvoiceId: ['', Validators.required],
    collectionDate: [new Date().toISOString().slice(0, 10), Validators.required],
    amount: ['0.00', Validators.required],
    paymentMode: ['UPI' as Collection['paymentMode'], Validators.required],
  });

  ngOnInit(): void {
    this.reloadInvoices();
    this.load();
    const params = this.route.snapshot.queryParamMap;
    if (params.get('create') === '1' && this.canEdit()) {
      this.openCreate();
      this.form.patchValue({ salesInvoiceId: params.get('salesInvoiceId') ?? '' });
      this.refreshOutstanding();
    }
    this.form.controls.salesInvoiceId.valueChanges.subscribe(() => this.refreshOutstanding());
    this.form.controls.amount.valueChanges.subscribe(() => this.refreshOutstanding());
  }

  load(): void {
    this.loading.set(true);
    this.api.listCollections({ page: this.page, search: this.search }).subscribe({
      next: (result) => {
        this.items = result.items;
        this.total = result.total;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load collections.');
      },
      });
  }

  onFilters(state: FilterBarState): void {
    this.search = state.search;
    this.page = 1;
    this.load();
  }

  openCreate(): void {
    this.form.reset({
      salesInvoiceId: '',
      collectionDate: new Date().toISOString().slice(0, 10),
      amount: '0.00',
      paymentMode: 'UPI',
    });
    this.amountError = '';
    this.modalOpen.set(true);
  }

  private reloadInvoices(): void {
    this.api.listSalesInvoices({ pageSize: 100 }).subscribe((result) => (this.invoices = result.items));
  }

  refreshOutstanding(): void {
    const invoiceId = this.form.controls.salesInvoiceId.value;
    const invoice = this.invoices.find((row) => row.id === invoiceId) ?? null;
    const summary = this.api.salesInvoiceOutstanding(invoice);
    this.invoiceAmount = summary?.invoiceAmount ?? '0.00';
    this.alreadyPaid = summary?.paid ?? '0.00';
    this.outstanding = summary?.outstanding ?? '0.00';
    const current = parseMoneyInput(this.form.controls.amount.value);
    this.remainingAfter = subtractMoney(this.outstanding, current);
    this.amountError = compareMoney(current, this.outstanding) > 0 ? 'Amount cannot exceed outstanding.' : '';
  }

  requestSave(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.refreshOutstanding();
    if (this.amountError) {
      return;
    }
    this.confirmOpen.set(true);
  }

  confirmSave(): void {
    const value = this.form.getRawValue();
    this.saving.set(true);
    this.api
      .createCollection({
        salesInvoiceId: value.salesInvoiceId,
        collectionDate: value.collectionDate,
        amount: parseMoneyInput(value.amount),
        paymentMode: value.paymentMode,
        status: 'completed',
      })
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.confirmOpen.set(false);
          this.modalOpen.set(false);
          this.toast.success('Collection recorded');
          this.reloadInvoices();
          this.load();
        },
        error: (err) => {
          this.saving.set(false);
          this.toast.error('Collection failed', err.message);
        },
      });
  }
}
