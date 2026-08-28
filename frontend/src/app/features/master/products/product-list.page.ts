import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

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
import { Product } from '../../finance/models/finance.model';
import { FinanceApiService } from '../../finance/services/finance-api.service';

@Component({
  selector: 'app-product-list-page',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    PageHeaderComponent,
    FilterBarComponent,
    StatusBadgeComponent,
    PaginationComponent,
    ModalComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
  ],
  templateUrl: './product-list.page.html',
})
export class ProductListPage implements OnInit {
  private readonly api = inject(FinanceApiService);
  private readonly toast = inject(ToastService);
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  readonly loading = signal(true);
  readonly error = signal('');
  readonly modalOpen = signal(false);
  readonly saving = signal(false);
  items: Product[] = [];
  total = 0;
  page = 1;
  search = '';
  status = '';
  editing: Product | null = null;
  readonly form = this.fb.nonNullable.group({
    name: ['', Validators.required],
    vinNumber: [''],
    model: [''],
    batteryType: [''],
    bodyColor: [''],
    status: ['active' as Product['status'], Validators.required],
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.listProducts({ page: this.page, search: this.search, status: this.status }).subscribe({
      next: (result) => {
        this.items = result.items;
        this.total = result.total;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load products.');
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
    this.form.reset({ name: '', vinNumber: '', model: '', batteryType: '', bodyColor: '', status: 'active' });
    this.modalOpen.set(true);
  }

  openEdit(_row: Product): void {
    this.toast.error('Updating a product is not supported by the API yet.');
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.api.saveProduct({ id: this.editing?.id, ...this.form.getRawValue() }).subscribe({
      next: () => {
        this.saving.set(false);
        this.modalOpen.set(false);
        this.toast.success(this.editing ? 'Product updated' : 'Product created');
        this.load();
      },
      error: (err) => {
        this.saving.set(false);
        this.toast.error('Save failed', err.message);
      },
    });
  }
}
