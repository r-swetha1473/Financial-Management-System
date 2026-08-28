import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { canMaintainReference } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { FilterBarComponent, FilterBarSelect, FilterBarState } from '../../../shared/components/filter-bar/filter-bar.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { P2pBannerComponent } from '../../p2p/components/p2p-banner.component';
import { Vendor } from '../../p2p/models/p2p.model';
import { P2pApiService } from '../../p2p/services/p2p-api.service';

@Component({
  selector: 'app-vendor-list-page',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    FormsModule,
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
  templateUrl: './vendor-list.page.html',
})
export class VendorListPage implements OnInit {
  private readonly api = inject(P2pApiService);
  private readonly toast = inject(ToastService);
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);

  readonly canEdit = computed(() => canMaintainReference(this.auth.session()?.role));
  readonly loading = signal(true);
  readonly error = signal('');
  readonly modalOpen = signal(false);
  readonly saving = signal(false);

  items: Vendor[] = [];
  total = 0;
  page = 1;
  readonly pageSize = 20;
  search = '';
  status = '';
  editing: Vendor | null = null;

  readonly form = this.fb.nonNullable.group({
    name: ['', Validators.required],
    address: [''],
    phone: [''],
    email: ['', Validators.email],
    pocName: [''],
    pocEmail: ['', Validators.email],
    gstin: [''],
    state: [''],
    status: ['active' as Vendor['status'], Validators.required],
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set('');
    this.api.listVendors({ page: this.page, pageSize: this.pageSize, search: this.search, status: this.status }).subscribe({
      next: (result) => {
        this.items = result.items;
        this.total = result.total;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load vendors.');
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
          { value: 'active', label: 'Active' },
          { value: 'inactive', label: 'Inactive' },
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
      name: '',
      address: '',
      phone: '',
      email: '',
      pocName: '',
      pocEmail: '',
      gstin: '',
      state: '',
      status: 'active',
    });
    this.modalOpen.set(true);
  }

  openEdit(vendor: Vendor): void {
    this.editing = vendor;
    this.form.patchValue({
      name: vendor.name,
      address: vendor.address ?? '',
      phone: vendor.phone ?? '',
      email: vendor.email ?? '',
      pocName: vendor.pocName ?? '',
      pocEmail: vendor.pocEmail ?? '',
      gstin: vendor.gstin ?? '',
      state: vendor.state ?? '',
      status: vendor.status,
    });
    this.modalOpen.set(true);
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.api.saveVendor({ id: this.editing?.id, ...this.form.getRawValue() }).subscribe({
      next: () => {
        this.saving.set(false);
        this.modalOpen.set(false);
        this.toast.success(this.editing ? 'Vendor updated' : 'Vendor created');
        this.load();
      },
      error: (err) => {
        this.saving.set(false);
        this.toast.error('Save failed', err.message);
      },
    });
  }
}
