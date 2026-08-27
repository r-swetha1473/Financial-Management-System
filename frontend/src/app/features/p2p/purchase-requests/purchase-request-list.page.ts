import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { P2pBannerComponent } from '../components/p2p-banner.component';
import { PurchaseRequest, Vendor } from '../models/p2p.model';
import { P2pApiService } from '../services/p2p-api.service';

@Component({
  selector: 'app-purchase-request-list-page',
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
  ],
  templateUrl: './purchase-request-list.page.html',
})
export class PurchaseRequestListPage implements OnInit {
  private readonly api = inject(P2pApiService);
  private readonly toast = inject(ToastService);
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);

  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  readonly canApprove = computed(() => hasPermission(this.auth.session()?.role, 'approve'));
  readonly loading = signal(true);
  readonly error = signal('');
  readonly modalOpen = signal(false);
  readonly saving = signal(false);

  items: PurchaseRequest[] = [];
  vendors: Vendor[] = [];
  total = 0;
  page = 1;
  search = '';
  status = '';
  vendorId = '';
  editing: PurchaseRequest | null = null;

  readonly form = this.fb.nonNullable.group({
    requestNumber: ['', Validators.required],
    vendorId: [''],
    requestedDate: [new Date().toISOString().slice(0, 10), Validators.required],
    status: ['approved' as PurchaseRequest['status'], Validators.required],
    notes: [''],
  });

  ngOnInit(): void {
    this.api.listVendors({ pageSize: 100 }).subscribe((result) => (this.vendors = result.items));
    const params = this.route.snapshot.queryParamMap;
    this.vendorId = params.get('vendorId') ?? '';
    this.load();
    if (params.get('create') === '1' && this.canEdit()) {
      this.openCreate();
      if (this.vendorId) {
        this.form.patchValue({ vendorId: this.vendorId });
      }
    }
  }

  load(): void {
    this.loading.set(true);
    this.api
      .listPurchaseRequests({ page: this.page, search: this.search, status: this.status, vendorId: this.vendorId })
      .subscribe({
        next: (result) => {
          this.items = result.items;
          this.total = result.total;
          this.loading.set(false);
        },
        error: () => {
          this.loading.set(false);
          this.error.set('Unable to load purchase requests.');
        },
      });
  }

  openCreate(): void {
    this.editing = null;
    this.form.reset({
      requestNumber: `PR-${new Date().getFullYear()}-${String(this.total + 1).padStart(3, '0')}`,
      vendorId: this.vendorId,
      requestedDate: new Date().toISOString().slice(0, 10),
      status: 'approved',
      notes: '',
    });
    this.modalOpen.set(true);
  }

  approve(row: PurchaseRequest): void {
    this.api.approvePurchaseRequest(row.id).subscribe({
      next: () => {
        this.toast.success('Purchase request approved');
        this.load();
      },
      error: (err) => this.toast.error('Approve failed', err.message),
    });
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    this.saving.set(true);
    this.api
      .savePurchaseRequest({
        requestNumber: value.requestNumber,
        vendorId: value.vendorId || null,
        requestedDate: value.requestedDate,
        status: value.status,
        notes: value.notes,
        requestedByName: this.auth.session()?.fullName ?? 'User',
      })
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.modalOpen.set(false);
          this.toast.success('Request created');
          this.load();
        },
        error: (err) => {
          this.saving.set(false);
          this.toast.error('Save failed', err.message);
        },
      });
  }
}
