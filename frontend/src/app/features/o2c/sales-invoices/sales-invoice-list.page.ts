import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

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
import { O2cBannerComponent } from '../components/o2c-banner.component';
import { Customer, Delivery, SalesInvoice, SalesOrder } from '../models/o2c.model';
import { O2cApiService } from '../services/o2c-api.service';

@Component({
  selector: 'app-sales-invoice-list-page',
  standalone: true,
  imports: [
    FormsModule,
    ReactiveFormsModule,
    RouterLink,
    PageHeaderComponent,
    O2cBannerComponent,
    StatusBadgeComponent,
    PaginationComponent,
    ModalComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
    InrPipe,
  ],
  templateUrl: './sales-invoice-list.page.html',
})
export class SalesInvoiceListPage implements OnInit {
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
  items: SalesInvoice[] = [];
  allInvoices: SalesInvoice[] = [];
  customers: Customer[] = [];
  orders: SalesOrder[] = [];
  deliveries: Delivery[] = [];
  total = 0;
  page = 1;
  search = '';
  status = '';
  customerId = '';
  editing: SalesInvoice | null = null;

  get invoiceableDeliveries(): Delivery[] {
    const invoiced = new Set(
      this.allInvoices
        .filter((invoice) => invoice.status !== 'cancelled' && invoice.deliveryId)
        .map((invoice) => invoice.deliveryId as string),
    );
    return this.deliveries.filter((delivery) => delivery.status === 'delivered' && !invoiced.has(delivery.id));
  }

  readonly form = this.fb.nonNullable.group({
    invoiceNumber: [''],
    customerId: [''],
    salesOrderId: [''],
    deliveryId: ['', Validators.required],
    invoiceDate: [new Date().toISOString().slice(0, 10), Validators.required],
    amount: ['0.00', Validators.required],
    gstAmount: ['0.00', Validators.required],
    status: ['pending' as SalesInvoice['status'], Validators.required],
  });

  ngOnInit(): void {
    this.api.listCustomers({ pageSize: 100 }).subscribe((result) => (this.customers = result.items));
    this.api.listSalesOrders({ pageSize: 100 }).subscribe((result) => (this.orders = result.items));
    this.api.listDeliveries({ pageSize: 100 }).subscribe((result) => (this.deliveries = result.items));
    this.api.listSalesInvoices({ pageSize: 100 }).subscribe((result) => (this.allInvoices = result.items));
    const params = this.route.snapshot.queryParamMap;
    this.customerId = params.get('customerId') ?? '';
    this.load();
    if (params.get('create') === '1' && this.canEdit()) {
      this.openCreate();
      this.form.patchValue({
        customerId: params.get('customerId') ?? '',
        salesOrderId: params.get('salesOrderId') ?? '',
        deliveryId: params.get('deliveryId') ?? '',
      });
    }
    this.form.controls.deliveryId.valueChanges.subscribe((deliveryId) => {
      const delivery = this.deliveries.find((row) => row.id === deliveryId);
      if (delivery) {
        this.form.patchValue(
          { salesOrderId: delivery.salesOrderId, customerId: delivery.customerId },
          { emitEvent: false },
        );
      }
    });
    this.form.controls.salesOrderId.valueChanges.subscribe((salesOrderId) => {
      const order = this.orders.find((row) => row.id === salesOrderId);
      if (order && !this.form.controls.customerId.value) {
        this.form.patchValue({ customerId: order.customerId, amount: order.totalAmount }, { emitEvent: false });
      }
    });
  }

  load(): void {
    this.loading.set(true);
    this.api
      .listSalesInvoices({ page: this.page, search: this.search, status: this.status, customerId: this.customerId })
      .subscribe({
        next: (result) => {
          this.items = result.items;
          this.total = result.total;
          this.loading.set(false);
        },
        error: () => {
          this.loading.set(false);
          this.error.set('Unable to load sales invoices.');
        },
      });
  }

  outstanding(row: SalesInvoice): string {
    return row.outstanding ?? row.amount;
  }

  openCreate(): void {
    this.editing = null;
    this.form.reset({
      invoiceNumber: `O2C-${new Date().getFullYear()}-${String(this.total + 1).padStart(4, '0')}`,
      customerId: this.customerId,
      salesOrderId: '',
      deliveryId: '',
      invoiceDate: new Date().toISOString().slice(0, 10),
      amount: '0.00',
      gstAmount: '0.00',
      status: 'pending',
    });
    this.modalOpen.set(true);
  }

  openEdit(row: SalesInvoice): void {
    this.editing = row;
    this.form.patchValue({
      invoiceNumber: row.invoiceNumber,
      customerId: row.customerId,
      salesOrderId: row.salesOrderId ?? '',
      deliveryId: row.deliveryId ?? '',
      invoiceDate: row.invoiceDate,
      amount: row.amount,
      gstAmount: row.gstAmount,
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
      .saveSalesInvoice({
        id: this.editing?.id,
        invoiceNumber: value.invoiceNumber,
        customerId: value.customerId,
        salesOrderId: value.salesOrderId || null,
        deliveryId: value.deliveryId || null,
        invoiceDate: value.invoiceDate,
        amount: parseMoneyInput(value.amount),
        gstAmount: parseMoneyInput(value.gstAmount),
        status: value.status,
      })
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.modalOpen.set(false);
          this.toast.success(this.editing ? 'Sales invoice updated' : 'Sales invoice recorded');
          this.api.listSalesInvoices({ pageSize: 100 }).subscribe((result) => (this.allInvoices = result.items));
          this.load();
        },
        error: (err) => {
          this.saving.set(false);
          this.toast.error('Save failed', err.message);
        },
      });
  }
}
