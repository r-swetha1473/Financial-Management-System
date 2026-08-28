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
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { InvoiceReceipt, LegacyInvoice } from '../../o2c/models/o2c.model';
import { O2cApiService } from '../../o2c/services/o2c-api.service';
import { ExistingSalesBannerComponent } from '../components/existing-sales-banner.component';

@Component({
  selector: 'app-receipt-list-page',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    PageHeaderComponent,
    ExistingSalesBannerComponent,
    FilterBarComponent,
    PaginationComponent,
    ModalComponent,
    ConfirmDialogComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
    InrPipe,
  ],
  templateUrl: './receipt-list.page.html',
})
export class ReceiptListPage implements OnInit {
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
  items: InvoiceReceipt[] = [];
  invoices: LegacyInvoice[] = [];
  total = 0;
  page = 1;
  search = '';
  invoiceAmount = '0.00';
  alreadyPaid = '0.00';
  outstanding = '0.00';
  remainingAfter = '0.00';
  amountError = '';
  upiError = '';

  readonly form = this.fb.nonNullable.group({
    invoiceId: ['', Validators.required],
    receiptDate: [new Date().toISOString().slice(0, 10), Validators.required],
    receiptAmount: ['0.00', Validators.required],
    paymentMode: ['UPI' as InvoiceReceipt['paymentMode'], Validators.required],
    transactionLast4: [''],
  });

  ngOnInit(): void {
    this.api.listInvoices({ pageSize: 100 }).subscribe((result) => (this.invoices = result.items));
    this.load();
    const params = this.route.snapshot.queryParamMap;
    if (params.get('create') === '1' && this.canEdit()) {
      this.openCreate();
      this.form.patchValue({ invoiceId: params.get('invoiceId') ?? '' });
      this.refreshOutstanding();
    }
    this.form.controls.invoiceId.valueChanges.subscribe(() => this.refreshOutstanding());
    this.form.controls.receiptAmount.valueChanges.subscribe(() => this.refreshOutstanding());
    this.form.controls.paymentMode.valueChanges.subscribe(() => this.refreshUpi());
    this.form.controls.transactionLast4.valueChanges.subscribe(() => this.refreshUpi());
  }

  load(): void {
    this.loading.set(true);
    this.api.listReceipts({ page: this.page, search: this.search }).subscribe({
      next: (result) => {
        this.items = result.items;
        this.total = result.total;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load receipts.');
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
      invoiceId: '',
      receiptDate: new Date().toISOString().slice(0, 10),
      receiptAmount: '0.00',
      paymentMode: 'UPI',
      transactionLast4: '',
    });
    this.amountError = '';
    this.upiError = '';
    this.modalOpen.set(true);
  }

  refreshOutstanding(): void {
    const invoiceId = this.form.controls.invoiceId.value;
    const invoice = this.invoices.find((row) => row.id === invoiceId) ?? null;
    const summary = this.api.legacyInvoiceOutstanding(invoice);
    this.invoiceAmount = summary?.invoiceAmount ?? '0.00';
    this.alreadyPaid = summary?.paid ?? '0.00';
    this.outstanding = summary?.outstanding ?? '0.00';
    const current = parseMoneyInput(this.form.controls.receiptAmount.value);
    this.remainingAfter = subtractMoney(this.outstanding, current);
    this.amountError = compareMoney(current, this.outstanding) > 0 ? 'Amount cannot exceed outstanding.' : '';
  }

  refreshUpi(): void {
    const mode = this.form.controls.paymentMode.value;
    const last4 = this.form.controls.transactionLast4.value.trim();
    this.upiError = mode === 'UPI' && !/^\d{4}$/.test(last4) ? 'UPI receipts require exactly 4 digits.' : '';
  }

  requestSave(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.refreshOutstanding();
    this.refreshUpi();
    if (this.amountError || this.upiError) {
      return;
    }
    this.confirmOpen.set(true);
  }

  confirmSave(): void {
    const value = this.form.getRawValue();
    this.saving.set(true);
    this.api
      .createReceipt({
        invoiceId: value.invoiceId,
        receiptDate: value.receiptDate,
        receiptAmount: parseMoneyInput(value.receiptAmount),
        paymentMode: value.paymentMode,
        transactionLast4: value.paymentMode === 'UPI' ? value.transactionLast4.trim() : '',
      })
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.confirmOpen.set(false);
          this.modalOpen.set(false);
          this.toast.success('Receipt recorded');
          this.load();
        },
        error: (err) => {
          this.saving.set(false);
          this.toast.error('Receipt failed', err.message);
        },
      });
  }
}
