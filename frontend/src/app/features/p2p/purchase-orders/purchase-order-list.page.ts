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
import { P2pBannerComponent } from '../components/p2p-banner.component';
import { PurchaseOrder, PurchaseRequest, Vendor } from '../models/p2p.model';
import { P2pApiService } from '../services/p2p-api.service';

@Component({
  selector: 'app-purchase-order-list-page',
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
  templateUrl: './purchase-order-list.page.html',
})
export class PurchaseOrderListPage implements OnInit {
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

  items: PurchaseOrder[] = [];
  vendors: Vendor[] = [];
  requests: PurchaseRequest[] = [];
  total = 0;
  page = 1;
  search = '';
  status = '';
  vendorId = '';
  editing: PurchaseOrder | null = null;

  get approvedRequests(): PurchaseRequest[] {
    return this.requests.filter((request) => request.status === 'approved');
  }

  readonly form = this.fb.nonNullable.group({
    poNumber: ['', Validators.required],
    vendorId: ['', Validators.required],
    purchaseRequestId: [''],
    orderDate: [new Date().toISOString().slice(0, 10), Validators.required],
    totalAmount: ['0.00', Validators.required],
    status: ['draft' as PurchaseOrder['status'], Validators.required],
  });

  ngOnInit(): void {
    this.api.listVendors({ pageSize: 100 }).subscribe((result) => (this.vendors = result.items));
    this.api.listPurchaseRequests({ pageSize: 100 }).subscribe((result) => {
      this.requests = result.items;
      const params = this.route.snapshot.queryParamMap;
      this.vendorId = params.get('vendorId') ?? '';
      if (params.get('create') === '1' && this.canEdit()) {
        this.openCreate();
        const purchaseRequestId = params.get('purchaseRequestId') ?? '';
        const request = this.approvedRequests.find((row) => row.id === purchaseRequestId);
        this.form.patchValue({
          vendorId: params.get('vendorId') ?? request?.vendorId ?? '',
          purchaseRequestId: request?.id ?? '',
          status: 'issued',
        });
        if (purchaseRequestId && !request) {
          this.toast.error('Purchase request must be approved before converting to a purchase order.');
        }
      }
    });
    const params = this.route.snapshot.queryParamMap;
    this.vendorId = params.get('vendorId') ?? '';
    this.load();
    this.form.controls.purchaseRequestId.valueChanges.subscribe((purchaseRequestId) => {
      const request = this.approvedRequests.find((row) => row.id === purchaseRequestId);
      if (request?.vendorId) {
        this.form.patchValue({ vendorId: request.vendorId }, { emitEvent: false });
      }
    });
  }

  load(): void {
    this.loading.set(true);
    this.api
      .listPurchaseOrders({ page: this.page, search: this.search, status: this.status, vendorId: this.vendorId })
      .subscribe({
        next: (result) => {
          this.items = result.items;
          this.total = result.total;
          this.loading.set(false);
        },
        error: () => {
          this.loading.set(false);
          this.error.set('Unable to load purchase orders.');
        },
      });
  }

  openCreate(): void {
    this.editing = null;
    this.form.reset({
      poNumber: `PO-${new Date().getFullYear()}-${String(this.total + 1).padStart(3, '0')}`,
      vendorId: this.vendorId,
      purchaseRequestId: '',
      orderDate: new Date().toISOString().slice(0, 10),
      totalAmount: '0.00',
      status: 'draft',
    });
    this.modalOpen.set(true);
  }

  openEdit(_row: PurchaseOrder): void {
    this.toast.error('Updating a purchase order is not supported by the API yet.');
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    if (this.editing) {
      this.toast.error('Updating a purchase order is not supported by the API yet.');
      return;
    }
    const value = this.form.getRawValue();
    const linked = this.approvedRequests.find((row) => row.id === value.purchaseRequestId);
    if (value.purchaseRequestId && !linked) {
      this.toast.error('Purchase request must be approved before converting to a purchase order.');
      return;
    }
    this.saving.set(true);
    this.api
      .savePurchaseOrder({
        poNumber: value.poNumber,
        vendorId: value.vendorId,
        purchaseRequestId: linked?.id ?? null,
        orderDate: value.orderDate,
        totalAmount: parseMoneyInput(value.totalAmount),
        status: value.status,
      })
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.modalOpen.set(false);
          this.toast.success('Purchase order created');
          this.load();
        },
        error: (err) => {
          this.saving.set(false);
          this.toast.error('Save failed', err.message);
        },
      });
  }
}
