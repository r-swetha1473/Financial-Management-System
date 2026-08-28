import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

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
import { P2pBannerComponent } from '../components/p2p-banner.component';
import { SupplierInvoice, SupplierPayment } from '../models/p2p.model';
import { P2pApiService } from '../services/p2p-api.service';

@Component({
  selector: 'app-payment-list-page',
  standalone: true,
  imports: [
    FormsModule,
    ReactiveFormsModule,
    RouterLink,
    PageHeaderComponent,
    P2pBannerComponent,
    FilterBarComponent,
    StatusBadgeComponent,
    PaginationComponent,
    ModalComponent,
    ConfirmDialogComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
    InrPipe,
  ],
  templateUrl: './payment-list.page.html',
})
export class PaymentListPage implements OnInit {
  private readonly api = inject(P2pApiService);
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

  items: SupplierPayment[] = [];
  invoices: SupplierInvoice[] = [];
  allPayments: SupplierPayment[] = [];
  total = 0;
  page = 1;
  search = '';
  invoiceAmount = '0.00';
  alreadyPaid = '0.00';
  outstanding = '0.00';
  remainingAfter = '0.00';
  amountError = '';

  get payableInvoices(): SupplierInvoice[] {
    return this.invoices.filter((invoice) => {
      if (invoice.approvalStatus !== 'approved' || invoice.status === 'paid' || invoice.status === 'cancelled') {
        return false;
      }
      const summary = this.api.invoiceOutstanding(invoice, this.allPayments);
      return !!summary && compareMoney(summary.outstanding, '0.00') > 0;
    });
  }

  readonly form = this.fb.nonNullable.group({
    supplierInvoiceId: ['', Validators.required],
    paymentDate: [new Date().toISOString().slice(0, 10), Validators.required],
    amount: ['0.00', Validators.required],
    paymentMode: ['UPI' as SupplierPayment['paymentMode'], Validators.required],
  });

  ngOnInit(): void {
    this.reloadLookups();
    this.load();
    const params = this.route.snapshot.queryParamMap;
    if (params.get('create') === '1' && this.canEdit()) {
      this.openCreate();
      this.form.patchValue({ supplierInvoiceId: params.get('supplierInvoiceId') ?? '' });
      this.refreshOutstanding();
    }
    this.form.controls.supplierInvoiceId.valueChanges.subscribe(() => this.refreshOutstanding());
    this.form.controls.amount.valueChanges.subscribe(() => this.refreshOutstanding());
  }

  load(): void {
    this.loading.set(true);
    this.api.listPayments({ page: this.page, search: this.search }).subscribe({
      next: (result) => {
        this.items = result.items;
        this.total = result.total;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
          this.error.set('Unable to load payments.');
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
      supplierInvoiceId: '',
      paymentDate: new Date().toISOString().slice(0, 10),
      amount: '0.00',
      paymentMode: 'UPI',
    });
    this.amountError = '';
    this.modalOpen.set(true);
  }

  refreshOutstanding(): void {
    const invoiceId = this.form.controls.supplierInvoiceId.value;
    const invoice = this.invoices.find((row) => row.id === invoiceId) ?? null;
    const summary = this.api.invoiceOutstanding(invoice, this.allPayments);
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
      .createPayment({
        supplierInvoiceId: value.supplierInvoiceId,
        paymentDate: value.paymentDate,
        amount: parseMoneyInput(value.amount),
        paymentMode: value.paymentMode,
        status: 'completed',
      })
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.confirmOpen.set(false);
          this.modalOpen.set(false);
          this.toast.success('Payment recorded');
          this.reloadLookups();
          this.load();
        },
        error: (err) => {
          this.saving.set(false);
          this.toast.error('Payment failed', err.message);
        },
      });
  }

  private reloadLookups(): void {
    forkJoin({
      invoices: this.api.listSupplierInvoices({ pageSize: 100 }),
      payments: this.api.listPayments({ pageSize: 100 }),
    }).subscribe({
      next: (data) => {
        this.invoices = data.invoices.items;
        this.allPayments = data.payments.items;
        this.refreshOutstanding();
      },
      error: (err) => this.toast.error('Unable to load invoices', err.message),
    });
  }
}
