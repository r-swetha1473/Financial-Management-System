import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { canMaintainReference } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { O2cBannerComponent } from '../../o2c/components/o2c-banner.component';
import { Customer } from '../../o2c/models/o2c.model';
import { O2cApiService } from '../../o2c/services/o2c-api.service';

@Component({
  selector: 'app-customer-list-page',
  standalone: true,
  imports: [
    FormsModule,
    ReactiveFormsModule,
    RouterLink,
    PageHeaderComponent,
    O2cBannerComponent,
    PaginationComponent,
    ModalComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
  ],
  templateUrl: './customer-list.page.html',
})
export class CustomerListPage implements OnInit {
  private readonly api = inject(O2cApiService);
  private readonly toast = inject(ToastService);
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);

  readonly canEdit = computed(() => canMaintainReference(this.auth.session()?.role));
  readonly loading = signal(true);
  readonly error = signal('');
  readonly modalOpen = signal(false);
  readonly saving = signal(false);
  items: Customer[] = [];
  total = 0;
  page = 1;
  readonly pageSize = 20;
  search = '';
  editing: Customer | null = null;

  readonly form = this.fb.nonNullable.group({
    name: ['', Validators.required],
    address: [''],
    gstin: [''],
    state: [''],
    creditLimit: [''],
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set('');
    this.api.listCustomers({ page: this.page, pageSize: this.pageSize }).subscribe({
      next: (result) => {
        this.items = result.items;
        this.total = result.total;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load customers.');
      },
    });
  }

  openCreate(): void {
    this.editing = null;
    this.form.reset({ name: '', address: '', gstin: '', state: '', creditLimit: '' });
    this.modalOpen.set(true);
  }

  openEdit(row: Customer): void {
    this.editing = row;
    this.form.patchValue({
      name: row.name,
      address: row.address ?? '',
      gstin: row.gstin ?? '',
      state: row.state ?? '',
      creditLimit: row.creditLimit ?? '',
    });
    this.modalOpen.set(true);
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    const value = this.form.getRawValue();
    this.api
      .saveCustomer({
        id: this.editing?.id,
        name: value.name,
        address: value.address || null,
        gstin: value.gstin || null,
        state: value.state || null,
        creditLimit: value.creditLimit || null,
      })
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.modalOpen.set(false);
          this.toast.success(this.editing ? 'Customer updated' : 'Customer created');
          this.load();
        },
        error: (err) => {
          this.saving.set(false);
          this.toast.error('Save failed', err.message);
        },
      });
  }
}
