import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { FilterBarComponent, FilterBarState } from '../../../shared/components/filter-bar/filter-bar.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { Category, Subcategory } from '../../finance/models/finance.model';
import { FinanceApiService } from '../../finance/services/finance-api.service';

@Component({
  selector: 'app-category-list-page',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    PageHeaderComponent,
    FilterBarComponent,
    StatusBadgeComponent,
    ModalComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
  ],
  templateUrl: './category-list.page.html',
})
export class CategoryListPage implements OnInit {
  private readonly api = inject(FinanceApiService);
  private readonly toast = inject(ToastService);
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  readonly loading = signal(true);
  readonly error = signal('');
  readonly categoryModal = signal(false);
  readonly subModal = signal(false);
  readonly saving = signal(false);
  categories: Category[] = [];
  subcategories: Subcategory[] = [];
  selectedCategoryId = '';
  search = '';
  page = 1;
  editingCategory: Category | null = null;
  editingSub: Subcategory | null = null;
  readonly categoryForm = this.fb.nonNullable.group({
    name: ['', Validators.required],
    description: [''],
    isActive: [true],
  });
  readonly subForm = this.fb.nonNullable.group({
    categoryId: ['', Validators.required],
    name: ['', Validators.required],
    description: [''],
    isActive: [true],
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.listCategories({ pageSize: 100 }).subscribe({
      next: (result) => {
        this.categories = result.items;
        this.selectedCategoryId = this.selectedCategoryId || this.categories[0]?.id || '';
        this.loadSubs();
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load categories.');
      },
    });
  }

  loadSubs(): void {
    this.api.listSubcategories({ pageSize: 100, categoryId: this.selectedCategoryId }).subscribe((result) => {
      this.subcategories = result.items;
    });
  }

  get visibleCategories(): Category[] {
    const query = this.search.trim().toLowerCase();
    if (!query) {
      return this.categories;
    }
    return this.categories.filter(
      (row) =>
        row.name.toLowerCase().includes(query) || (row.description ?? '').toLowerCase().includes(query),
    );
  }

  onFilters(state: FilterBarState): void {
    this.search = state.search;
    this.page = 1;
    this.load();
  }

  openCategory(row?: Category): void {
    if (row) {
      this.toast.error('Updating a category is not supported by the API yet.');
      return;
    }
    this.editingCategory = null;
    this.categoryForm.reset({ name: '', description: '', isActive: true });
    this.categoryModal.set(true);
  }

  openSub(row?: Subcategory): void {
    if (row) {
      this.toast.error('Updating a subcategory is not supported by the API yet.');
      return;
    }
    this.editingSub = null;
    this.subForm.reset({
      categoryId: this.selectedCategoryId,
      name: '',
      description: '',
      isActive: true,
    });
    this.subModal.set(true);
  }

  saveCategory(): void {
    if (this.categoryForm.invalid) {
      this.categoryForm.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.api.saveCategory({ id: this.editingCategory?.id, ...this.categoryForm.getRawValue() }).subscribe({
      next: () => {
        this.saving.set(false);
        this.categoryModal.set(false);
        this.toast.success('Category saved');
        this.load();
      },
      error: (err) => {
        this.saving.set(false);
        this.toast.error('Save failed', err.message);
      },
    });
  }

  saveSub(): void {
    if (this.subForm.invalid) {
      this.subForm.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.api.saveSubcategory({ id: this.editingSub?.id, ...this.subForm.getRawValue() }).subscribe({
      next: () => {
        this.saving.set(false);
        this.subModal.set(false);
        this.toast.success('Subcategory saved');
        this.loadSubs();
      },
      error: (err) => {
        this.saving.set(false);
        this.toast.error('Save failed', err.message);
      },
    });
  }
}
