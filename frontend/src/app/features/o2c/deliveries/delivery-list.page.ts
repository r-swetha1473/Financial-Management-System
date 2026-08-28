import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
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
import { O2cBannerComponent } from '../components/o2c-banner.component';
import { Delivery, SalesOrder } from '../models/o2c.model';
import { O2cApiService } from '../services/o2c-api.service';

@Component({
  selector: 'app-delivery-list-page',
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
  ],
  templateUrl: './delivery-list.page.html',
})
export class DeliveryListPage implements OnInit {
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
  items: Delivery[] = [];
  orders: SalesOrder[] = [];
  total = 0;
  page = 1;
  readonly pageSize = 20;
  search = '';
  status = '';
  editing: Delivery | null = null;

  get deliverableOrders(): SalesOrder[] {
    return this.orders.filter((order) => order.status === 'confirmed' || order.status === 'fulfilled');
  }

  readonly form = this.fb.nonNullable.group({
    deliveryNumber: ['', Validators.required],
    salesOrderId: ['', Validators.required],
    deliveryDate: [new Date().toISOString().slice(0, 10), Validators.required],
    status: ['delivered' as Delivery['status'], Validators.required],
  });

  ngOnInit(): void {
    this.api.listSalesOrders({ pageSize: 100 }).subscribe((result) => (this.orders = result.items));
    this.load();
    const params = this.route.snapshot.queryParamMap;
    if (params.get('create') === '1' && this.canEdit()) {
      this.openCreate();
      this.form.patchValue({ salesOrderId: params.get('salesOrderId') ?? '' });
    }
  }

  load(): void {
    this.loading.set(true);
    this.api.listDeliveries({ page: this.page, pageSize: this.pageSize }).subscribe({
      next: (result) => {
        const query = this.search.trim().toLowerCase();
        this.items = result.items.filter((row) => {
          if (this.status && row.status !== this.status) {
            return false;
          }
          if (!query) {
            return true;
          }
          return (
            row.deliveryNumber.toLowerCase().includes(query) ||
            row.orderNumber.toLowerCase().includes(query) ||
            row.customerName.toLowerCase().includes(query)
          );
        });
        this.total = result.total;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load deliveries.');
      },
    });
  }

  get filterSelects(): FilterBarSelect[] {
    return [
      {
        key: 'status',
        label: 'Status',
        blankLabel: 'All statuses',
        value: this.status,
        options: [
          { value: 'delivered', label: 'Delivered' },
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
    this.editing = null;
    this.form.reset({
      deliveryNumber: `DN-${new Date().getFullYear()}-${String(this.total + 1).padStart(3, '0')}`,
      salesOrderId: '',
      deliveryDate: new Date().toISOString().slice(0, 10),
      status: 'delivered',
    });
    this.modalOpen.set(true);
  }

  openEdit(row: Delivery): void {
    this.editing = row;
    this.form.patchValue({
      deliveryNumber: row.deliveryNumber,
      salesOrderId: row.salesOrderId,
      deliveryDate: row.deliveryDate,
      status: row.status,
    });
    this.modalOpen.set(true);
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.api.saveDelivery({ id: this.editing?.id, ...this.form.getRawValue() }).subscribe({
      next: () => {
        this.saving.set(false);
        this.modalOpen.set(false);
        this.toast.success(this.editing ? 'Delivery updated' : 'Delivery recorded');
        this.load();
      },
      error: (err) => {
        this.saving.set(false);
        this.toast.error('Save failed', err.message);
      },
    });
  }
}
