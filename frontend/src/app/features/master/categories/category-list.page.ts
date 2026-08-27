import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
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
    FormsModule,
    ReactiveFormsModule,
    PageHeaderComponent,
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

  openCategory(row?: Category): void {
    this.editingCategory = row ?? null;
    this.categoryForm.reset({ name: row?.name ?? '', description: row?.description ?? '', isActive: row?.isActive ?? true });
    this.categoryModal.set(true);
  }

  openSub(row?: Subcategory): void {
    this.editingSub = row ?? null;
    this.subForm.reset({
      categoryId: row?.categoryId ?? this.selectedCategoryId,
      name: row?.name ?? '',
      description: row?.description ?? '',
      isActive: row?.isActive ?? true,
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
