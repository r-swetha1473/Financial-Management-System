import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { PublicOrgUser, USER_ROLES } from '../models/admin.model';
import { AdminApiService } from '../services/admin-api.service';

@Component({
  selector: 'app-user-list-page',
  standalone: true,
  imports: [
    FormsModule,
    ReactiveFormsModule,
    PageHeaderComponent,
    StatusBadgeComponent,
    PaginationComponent,
    ModalComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
  ],
  templateUrl: './user-list.page.html',
})
export class UserListPage implements OnInit {
  private readonly api = inject(AdminApiService);
  private readonly toast = inject(ToastService);
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'admin'));
  readonly roles = USER_ROLES;
  readonly loading = signal(true);
  readonly error = signal('');
  readonly modalOpen = signal(false);
  readonly saving = signal(false);
  items: PublicOrgUser[] = [];
  total = 0;
  page = 1;
  search = '';
  status = '';
  role = '';
  editing: PublicOrgUser | null = null;
  readonly form = this.fb.nonNullable.group({
    username: ['', [Validators.required, Validators.pattern(/^[a-zA-Z0-9._-]+$/)]],
    email: ['', [Validators.required, Validators.email]],
    fullName: ['', Validators.required],
    role: ['OPERATOR' as PublicOrgUser['role'], Validators.required],
    isActive: [true],
    password: [''],
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.listUsers({ page: this.page, search: this.search, status: this.status, role: this.role }).subscribe({
      next: (result) => {
        this.items = result.items;
        this.total = result.total;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load users.');
      },
    });
  }

  openCreate(): void {
    this.editing = null;
    this.form.reset({
      username: '',
      email: '',
      fullName: '',
      role: 'OPERATOR',
      isActive: true,
      password: '',
    });
    this.form.controls.password.setValidators([Validators.required, Validators.minLength(6)]);
    this.form.controls.password.updateValueAndValidity();
    this.modalOpen.set(true);
  }

  openEdit(row: PublicOrgUser): void {
    this.editing = row;
    this.form.reset({
      username: row.username,
      email: row.email,
      fullName: row.fullName,
      role: row.role,
      isActive: row.isActive,
      password: '',
    });
    this.form.controls.password.setValidators([Validators.minLength(6)]);
    this.form.controls.password.updateValueAndValidity();
    this.modalOpen.set(true);
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    this.saving.set(true);
    this.api
      .saveUser({
        id: this.editing?.id,
        username: value.username,
        email: value.email,
        fullName: value.fullName,
        role: value.role,
        isActive: value.isActive,
        password: value.password.trim() || undefined,
      })
      .subscribe({
        next: (saved) => {
          this.saving.set(false);
          this.modalOpen.set(false);
          this.toast.success(this.editing ? 'User updated' : 'User created');
          this.auth.syncCurrentUser(saved);
          this.load();
        },
        error: (err) => {
          this.saving.set(false);
          this.toast.error('Save failed', err.message);
        },
      });
  }
}
