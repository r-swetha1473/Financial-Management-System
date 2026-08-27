import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { AdminApiService } from '../services/admin-api.service';

@Component({
  selector: 'app-settings-page',
  standalone: true,
  imports: [FormsModule, ReactiveFormsModule, PageHeaderComponent, LoadingSkeletonComponent],
  templateUrl: './settings.page.html',
})
export class SettingsPage implements OnInit {
  private readonly api = inject(AdminApiService);
  private readonly auth = inject(AuthService);
  private readonly toast = inject(ToastService);
  private readonly fb = inject(FormBuilder);
  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'admin'));
  readonly loading = signal(true);
  readonly error = signal('');
  readonly saving = signal(false);
  readonly form = this.fb.nonNullable.group({
    name: ['', Validators.required],
    slug: ['', [Validators.required, Validators.pattern(/^[a-z0-9]+(?:-[a-z0-9]+)*$/)]],
    isActive: [true],
  });

  ngOnInit(): void {
    this.api.getOrganization().subscribe({
      next: (org) => {
        this.form.reset({ name: org.name, slug: org.slug, isActive: org.isActive });
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load organization settings.');
      },
    });
  }

  save(): void {
    if (!this.canEdit() || this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.api.saveOrganization(this.form.getRawValue()).subscribe({
      next: (org) => {
        this.saving.set(false);
        this.auth.updateSession({ organizationName: org.name, organizationId: org.id });
        this.toast.success('Organization updated');
      },
      error: (err) => {
        this.saving.set(false);
        this.toast.error('Save failed', err.message);
      },
    });
  }
}
