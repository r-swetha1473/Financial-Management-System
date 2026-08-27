import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { parseMoneyInput } from '../../../core/utils/money.util';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { P2pBannerComponent } from '../components/p2p-banner.component';
import { GoodsReceipt, SupplierInvoice, Vendor } from '../models/p2p.model';
import { P2pApiService } from '../services/p2p-api.service';

@Component({
  selector: 'app-supplier-invoice-list-page',
  standalone: true,
  imports: [
    FormsModule,
    ReactiveFormsModule,
    RouterLink,
    PageHeaderComponent,
    P2pBannerComponent,
    StatusBadgeComponent,
    PaginationComponent,
    ModalComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
    InrPipe,
  ],
  templateUrl: './supplier-invoice-list.page.html',
})
export class SupplierInvoiceListPage implements OnInit {
  private readonly api = inject(P2pApiService);
  private readonly toast = inject(ToastService);
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);

  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  readonly loading = signal(true);
  readonly error = signal('');
  readonly modalOpen = signal(false);
  readonly saving = signal(false);

  items: SupplierInvoice[] = [];
  allInvoices: SupplierInvoice[] = [];
  vendors: Vendor[] = [];
  receipts: GoodsReceipt[] = [];
  total = 0;
  page = 1;
  search = '';
  status = '';
  vendorId = '';

  get invoiceableReceipts(): GoodsReceipt[] {
    const invoiced = new Set(
      this.allInvoices
        .filter((invoice) => invoice.status !== 'cancelled' && invoice.goodsReceiptId)
        .map((invoice) => invoice.goodsReceiptId as string),
    );
    return this.receipts.filter((receipt) => receipt.status === 'received' && !invoiced.has(receipt.id));
  }

  readonly form = this.fb.nonNullable.group({
    invoiceNumber: [''],
    vendorId: [{ value: '', disabled: true }, Validators.required],
    goodsReceiptId: ['', Validators.required],
    invoiceDate: [new Date().toISOString().slice(0, 10), Validators.required],
    amount: ['0.00', Validators.required],
    gstAmount: ['0.00', Validators.required],
  });

  ngOnInit(): void {
    this.reloadLookups();
    const params = this.route.snapshot.queryParamMap;
    this.vendorId = params.get('vendorId') ?? '';
    this.load();
    this.form.controls.goodsReceiptId.valueChanges.subscribe((goodsReceiptId) => {
      const receipt = this.receipts.find((row) => row.id === goodsReceiptId);
      if (receipt) {
        this.form.patchValue({ vendorId: receipt.vendorId }, { emitEvent: false });
      }
    });
    if (params.get('create') === '1' && this.canEdit()) {
      this.openCreate();
      this.form.patchValue({
        vendorId: params.get('vendorId') ?? '',
        goodsReceiptId: params.get('goodsReceiptId') ?? '',
      });
    }
  }

  load(): void {
    this.loading.set(true);
    this.api
      .listSupplierInvoices({ page: this.page, search: this.search, status: this.status, vendorId: this.vendorId })
      .subscribe({
        next: (result) => {
          this.items = result.items;
          this.total = result.total;
          this.loading.set(false);
        },
        error: () => {
          this.loading.set(false);
          this.error.set('Unable to load supplier invoices.');
        },
      });
  }

  openCreate(): void {
    this.form.reset({
      invoiceNumber: `SI-${new Date().getFullYear()}-${String(this.total + 1).padStart(3, '0')}`,
      vendorId: this.vendorId,
      goodsReceiptId: '',
      invoiceDate: new Date().toISOString().slice(0, 10),
      amount: '0.00',
      gstAmount: '0.00',
    });
    this.modalOpen.set(true);
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    if (!this.invoiceableReceipts.some((receipt) => receipt.id === value.goodsReceiptId)) {
      this.toast.error('Save failed', 'Select a received goods receipt that is not already invoiced.');
      return;
    }
    this.saving.set(true);
    this.api
      .saveSupplierInvoice({
        goodsReceiptId: value.goodsReceiptId,
        vendorId: value.vendorId,
        invoiceDate: value.invoiceDate,
        amount: parseMoneyInput(value.amount),
        gstAmount: parseMoneyInput(value.gstAmount),
      })
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.modalOpen.set(false);
          this.toast.success('Invoice recorded');
          this.reloadLookups();
          this.load();
        },
        error: (err) => {
          this.saving.set(false);
          this.toast.error('Save failed', err.message);
        },
      });
  }

  private reloadLookups(): void {
    forkJoin({
      vendors: this.api.listVendors({ pageSize: 100 }),
      receipts: this.api.listGoodsReceipts({ pageSize: 100 }),
      invoices: this.api.listSupplierInvoices({ pageSize: 100 }),
    }).subscribe({
      next: (data) => {
        this.vendors = data.vendors.items;
        this.receipts = data.receipts.items;
        this.allInvoices = data.invoices.items;
        const requested = this.form.controls.goodsReceiptId.value;
        if (requested && !this.invoiceableReceipts.some((receipt) => receipt.id === requested)) {
          this.form.patchValue({ goodsReceiptId: '' });
          this.toast.error('Goods receipt must be received and not already invoiced.');
        }
      },
      error: (err) => this.toast.error('Unable to load receipts', err.message),
    });
  }
}
