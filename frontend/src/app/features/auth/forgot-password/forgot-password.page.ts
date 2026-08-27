import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { ToastService } from '../../../core/ui/toast.service';

import { BrandMarkComponent } from '../../../shared/components/brand-mark/brand-mark.component';

@Component({
  selector: 'app-forgot-password-page',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, BrandMarkComponent],
  templateUrl: './forgot-password.page.html',
})
export class ForgotPasswordPage {
  private readonly fb = inject(FormBuilder);
  private readonly toast = inject(ToastService);

  readonly submitted = signal(false);
  readonly form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
  });

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.submitted.set(true);
    this.toast.info('Request received', 'If an account exists, reset instructions will be sent.');
  }
}
