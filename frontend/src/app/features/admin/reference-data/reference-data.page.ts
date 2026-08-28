import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';

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
import { ReferenceDatum } from '../models/admin.model';
import { AdminApiService } from '../services/admin-api.service';

@Component({
  selector: 'app-reference-data-page',
  standalone: true,
  imports: [
    FormsModule,
    ReactiveFormsModule,
    PageHeaderComponent,
    FilterBarComponent,
    StatusBadgeComponent,
    PaginationComponent,
    ModalComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
  ],
  templateUrl: './reference-data.page.html',
})
export class ReferenceDataPage implements OnInit {
  private readonly api = inject(AdminApiService);
  private readonly toast = inject(ToastService);
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  readonly canEdit = computed(() => canMaintainReference(this.auth.session()?.role));
  readonly loading = signal(true);
  readonly error = signal('');
  readonly modalOpen = signal(false);
  readonly saving = signal(false);
  items: ReferenceDatum[] = [];
  total = 0;
  page = 1;
  search = '';
  status = '';
  dataType = '';
  editing: ReferenceDatum | null = null;
  readonly form = this.fb.nonNullable.group({
    dataType: ['', Validators.required],
    code: ['', Validators.required],
    label: ['', Validators.required],
    isActive: [true],
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.listReference({ page: this.page, search: this.search, status: this.status, dataType: this.dataType }).subscribe({
      next: (result) => {
        this.items = result.items;
        this.total = result.total;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load reference data.');
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
    this.dataType = '';
    this.status = state.values['status'] ?? '';
    this.page = 1;
    this.load();
  }

  openCreate(): void {
    this.editing = null;
    this.form.reset({ dataType: this.dataType, code: '', label: '', isActive: true });
    this.modalOpen.set(true);
  }

  openEdit(_row: ReferenceDatum): void {
    this.toast.error('Updating reference data is not supported by the API yet.');
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.api.saveReference({ id: this.editing?.id, ...this.form.getRawValue() }).subscribe({
      next: () => {
        this.saving.set(false);
        this.modalOpen.set(false);
        this.toast.success(this.editing ? 'Lookup updated' : 'Lookup created');
        this.load();
      },
      error: (err) => {
        this.saving.set(false);
        this.toast.error('Save failed', err.message);
      },
    });
  }
}
