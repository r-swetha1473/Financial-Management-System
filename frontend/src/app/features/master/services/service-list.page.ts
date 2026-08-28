import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { parseMoneyInput } from '../../../core/utils/money.util';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { FilterBarComponent, FilterBarState } from '../../../shared/components/filter-bar/filter-bar.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { Offering, Product } from '../../finance/models/finance.model';
import { FinanceApiService } from '../../finance/services/finance-api.service';

@Component({
  selector: 'app-service-list-page',
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
    InrPipe,
  ],
  templateUrl: './service-list.page.html',
})
export class ServiceListPage implements OnInit {
  private readonly api = inject(FinanceApiService);
  private readonly toast = inject(ToastService);
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  readonly loading = signal(true);
  readonly error = signal('');
  readonly modalOpen = signal(false);
  readonly saving = signal(false);
  items: Offering[] = [];
  products: Product[] = [];
  total = 0;
  page = 1;
  search = '';
  editing: Offering | null = null;
  readonly form = this.fb.nonNullable.group({
    name: ['', Validators.required],
    productId: [''],
    description: [''],
    amount: ['0.00', Validators.required],
    isActive: [true],
  });

  ngOnInit(): void {
    this.api.listProducts({ pageSize: 100 }).subscribe((result) => (this.products = result.items));
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.listOfferings({ page: this.page, search: this.search }).subscribe({
      next: (result) => {
        const query = this.search.trim().toLowerCase();
        this.items = query
          ? result.items.filter(
              (row) =>
                row.name.toLowerCase().includes(query) || (row.productName ?? '').toLowerCase().includes(query),
            )
          : result.items;
        this.total = result.total;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load services.');
      },
      });
  }

  onFilters(state: FilterBarState): void {
    this.search = state.search;
    this.page = 1;
    this.load();
  }

  openCreate(): void {
    this.editing = null;
    this.form.reset({ name: '', productId: '', description: '', amount: '0.00', isActive: true });
    this.modalOpen.set(true);
  }

  openEdit(_row: Offering): void {
    this.toast.error('Updating a service offering is not supported by the API yet.');
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    this.saving.set(true);
    this.api
      .saveOffering({
        id: this.editing?.id,
        name: value.name,
        productId: value.productId || null,
        description: value.description,
        amount: parseMoneyInput(value.amount),
        isActive: value.isActive,
      })
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.modalOpen.set(false);
          this.toast.success('Service offering saved');
          this.load();
        },
        error: (err) => {
          this.saving.set(false);
          this.toast.error('Save failed', err.message);
        },
      });
  }
}
