import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Observable, forkJoin, of } from 'rxjs';
import { map, switchMap } from 'rxjs/operators';

import { DocumentsApiService } from '../../../core/api/documents-api.service';
import { AuthService } from '../../../core/auth/auth.service';
import { canMaintainReference } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { isValidOptionalMoney } from '../../../core/utils/money.util';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { FilterBarComponent, FilterBarState } from '../../../shared/components/filter-bar/filter-bar.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { O2cBannerComponent } from '../../o2c/components/o2c-banner.component';
import { Customer } from '../../o2c/models/o2c.model';
import { O2cApiService } from '../../o2c/services/o2c-api.service';

const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
const PHOTO_MIMES = ['image/jpeg', 'image/png'];
const PROOF_MIMES = [...PHOTO_MIMES, 'application/pdf'];
const PHOTO_EXTS = ['.png', '.jpg', '.jpeg'];
const PROOF_EXTS = [...PHOTO_EXTS, '.pdf'];

function optionalMoney(control: AbstractControl): ValidationErrors | null {
  return isValidOptionalMoney(String(control.value ?? '')) ? null : { money: true };
}

@Component({
  selector: 'app-customer-list-page',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    PageHeaderComponent,
    O2cBannerComponent,
    FilterBarComponent,
    PaginationComponent,
    ModalComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
  ],
  templateUrl: './customer-list.page.html',
})
export class CustomerListPage implements OnInit {
  private readonly api = inject(O2cApiService);
  private readonly documents = inject(DocumentsApiService);
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
  photoFile: File | null = null;
  addressProofFile: File | null = null;
  fileError = '';

  readonly form = this.fb.nonNullable.group({
    name: ['', Validators.required],
    address: [''],
    state: [''],
    phone: [''],
    driversLicenseNumber: [''],
    creditLimit: ['', optionalMoney],
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set('');
    this.api.listCustomers({ page: this.page, pageSize: this.pageSize }).subscribe({
      next: (result) => {
        const query = this.search.trim().toLowerCase();
        this.items = query
          ? result.items.filter(
              (row) =>
                row.name.toLowerCase().includes(query) ||
                (row.address ?? '').toLowerCase().includes(query) ||
                (row.phone ?? '').toLowerCase().includes(query) ||
                (row.gstin ?? '').toLowerCase().includes(query),
            )
          : result.items;
        this.total = result.total;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load customers.');
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
    this.photoFile = null;
    this.addressProofFile = null;
    this.fileError = '';
    this.form.reset({
      name: '',
      address: '',
      state: '',
      phone: '',
      driversLicenseNumber: '',
      creditLimit: '',
    });
    this.modalOpen.set(true);
  }

  openEdit(row: Customer): void {
    this.editing = row;
    this.photoFile = null;
    this.addressProofFile = null;
    this.fileError = '';
    this.form.patchValue({
      name: row.name,
      address: row.address ?? '',
      state: row.state ?? '',
      phone: row.phone ?? '',
      driversLicenseNumber: row.driversLicenseNumber ?? '',
      creditLimit: row.creditLimit ?? '',
    });
    this.modalOpen.set(true);
  }

  onPhotoSelected(event: Event): void {
    this.photoFile = this.takeFile(event, PHOTO_MIMES, PHOTO_EXTS, 'Choose a PNG or JPEG, 10 MB max.');
  }

  onAddressProofSelected(event: Event): void {
    this.addressProofFile = this.takeFile(
      event,
      PROOF_MIMES,
      PROOF_EXTS,
      'Choose a PNG, JPEG, or PDF, 10 MB max.',
    );
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    if (this.fileError) {
      return;
    }
    this.saving.set(true);
    const value = this.form.getRawValue();
    this.api
      .saveCustomer({
        id: this.editing?.id,
        name: value.name,
        address: value.address || null,
        gstin: null,
        state: value.state || null,
        phone: value.phone || null,
        driversLicenseNumber: value.driversLicenseNumber || null,
        creditLimit: value.creditLimit.trim() || null,
        photoFileName: this.editing?.photoFileName ?? null,
        photoMimeType: this.editing?.photoMimeType ?? null,
        photoDocumentId: this.editing?.photoDocumentId ?? null,
      })
      .pipe(switchMap((customer) => this.uploadKyc(customer)))
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

  get creditLimitError(): string {
    const control = this.form.controls.creditLimit;
    if (!control.touched || !control.errors?.['money']) {
      return '';
    }
    return 'Enter a non-negative number.';
  }

  private uploadKyc(customer: Customer): Observable<Customer> {
    const jobs: Observable<unknown>[] = [];
    if (this.photoFile) {
      jobs.push(this.documents.upload(this.photoFile, 'customer', customer.id, 'photo'));
    }
    if (this.addressProofFile) {
      jobs.push(this.documents.upload(this.addressProofFile, 'customer', customer.id, 'address_proof'));
    }
    if (jobs.length === 0) {
      return of(customer);
    }
    return forkJoin(jobs).pipe(
      switchMap(() => this.api.getCustomer(customer.id)),
      map((row) => row ?? customer),
    );
  }

  private takeFile(event: Event, allowedMimes: string[], allowedExts: string[], typeMessage: string): File | null {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    this.fileError = '';
    if (!file) {
      return null;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      this.fileError = 'Each file must be 10 MB or smaller.';
      input.value = '';
      return null;
    }
    const ext = file.name.includes('.') ? file.name.slice(file.name.lastIndexOf('.')).toLowerCase() : '';
    const mimeOk = !file.type || allowedMimes.includes(file.type);
    const extOk = !ext || allowedExts.includes(ext);
    if (!mimeOk || !extOk) {
      this.fileError = typeMessage;
      input.value = '';
      return null;
    }
    return file;
  }
}
