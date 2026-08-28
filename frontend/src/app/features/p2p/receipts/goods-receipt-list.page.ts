import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { FilterBarComponent, FilterBarSelect, FilterBarState } from '../../../shared/components/filter-bar/filter-bar.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { P2pBannerComponent } from '../components/p2p-banner.component';
import { GoodsReceipt, PurchaseOrder } from '../models/p2p.model';
import { P2pApiService } from '../services/p2p-api.service';

@Component({
  selector: 'app-goods-receipt-list-page',
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
    EmptyStateComponent,
    LoadingSkeletonComponent,
  ],
  templateUrl: './goods-receipt-list.page.html',
})
export class GoodsReceiptListPage implements OnInit {
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

  items: GoodsReceipt[] = [];
  orders: PurchaseOrder[] = [];
  total = 0;
  page = 1;
  search = '';
  status = '';

  get receivableOrders(): PurchaseOrder[] {
    return this.orders.filter((order) => order.status === 'issued');
  }

  readonly form = this.fb.nonNullable.group({
    grnNumber: ['', Validators.required],
    purchaseOrderId: ['', Validators.required],
    receiptDate: [new Date().toISOString().slice(0, 10), Validators.required],
    status: ['received' as GoodsReceipt['status'], Validators.required],
  });

  ngOnInit(): void {
    this.reloadOrders();
    this.load();
    const params = this.route.snapshot.queryParamMap;
    if (params.get('create') === '1' && this.canEdit()) {
      this.openCreate();
      const purchaseOrderId = params.get('purchaseOrderId') ?? '';
      this.form.patchValue({ purchaseOrderId });
    }
  }

  private reloadOrders(): void {
    this.api.listPurchaseOrders({ pageSize: 100 }).subscribe({
      next: (result) => {
        this.orders = result.items;
        const requested = this.form.controls.purchaseOrderId.value;
        if (requested && !this.receivableOrders.some((order) => order.id === requested)) {
          this.form.patchValue({ purchaseOrderId: '' });
          this.toast.error('Purchase order must be issued before a goods receipt can be recorded.');
        }
      },
      error: (err) => this.toast.error('Unable to load purchase orders', err.message),
    });
  }

  load(): void {
    this.loading.set(true);
    this.api.listGoodsReceipts({ page: this.page, search: this.search, status: this.status }).subscribe({
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

  get filterSelects(): FilterBarSelect[] {
    return [
      {
        key: 'status',
        label: 'Status',
        blankLabel: 'All Statuses',
        value: this.status,
        options: [
          { value: 'received', label: 'Received' },
          { value: 'cancelled', label: 'Cancelled' },
        ],
      },
    ];
  }

  onFilters(state: FilterBarState): void {
    this.search = state.search;
    this.status = state.values['status'] ?? '';
    this.page = 1;
    this.load();
  }

  openCreate(): void {
    this.form.reset({
      grnNumber: `GRN-${new Date().getFullYear()}-${String(this.total + 1).padStart(3, '0')}`,
      purchaseOrderId: '',
      receiptDate: new Date().toISOString().slice(0, 10),
      status: 'received',
    });
    this.modalOpen.set(true);
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.api.saveGoodsReceipt(this.form.getRawValue()).subscribe({
      next: () => {
        this.saving.set(false);
        this.modalOpen.set(false);
        this.toast.success('Receipt recorded');
        this.reloadOrders();
        this.load();
      },
      error: (err) => {
        this.saving.set(false);
        this.toast.error('Save failed', err.message);
      },
    });
  }
}
