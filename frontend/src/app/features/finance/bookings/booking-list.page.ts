import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { parseMoneyInput } from '../../../core/utils/money.util';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { Booking, Customer, OfferingRef } from '../../o2c/models/o2c.model';
import { O2cApiService } from '../../o2c/services/o2c-api.service';
import { ExistingSalesBannerComponent } from '../components/existing-sales-banner.component';

@Component({
  selector: 'app-booking-list-page',
  standalone: true,
  imports: [
    FormsModule,
    ReactiveFormsModule,
    RouterLink,
    PageHeaderComponent,
    ExistingSalesBannerComponent,
    PaginationComponent,
    ModalComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
    InrPipe,
  ],
  templateUrl: './booking-list.page.html',
})
export class BookingListPage implements OnInit {
  private readonly api = inject(O2cApiService);
  private readonly toast = inject(ToastService);
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);

  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  readonly loading = signal(true);
  readonly error = signal('');
  readonly modalOpen = signal(false);
  readonly saving = signal(false);
  items: Booking[] = [];
  customers: Customer[] = [];
  offerings: OfferingRef[] = [];
  total = 0;
  page = 1;
  search = '';
  customerId = '';
  editing: Booking | null = null;

  readonly form = this.fb.nonNullable.group({
    offeringId: [''],
    customerId: [''],
    bookingStartDate: ['', Validators.required],
    bookingEndDate: ['', Validators.required],
    securityPaid: ['0.00', Validators.required],
  });

  ngOnInit(): void {
    this.offerings = this.api.offerings();
    this.api.listCustomers({ pageSize: 100 }).subscribe((result) => (this.customers = result.items));
    const params = this.route.snapshot.queryParamMap;
    this.customerId = params.get('customerId') ?? '';
    this.load();
    if (params.get('create') === '1' && this.canEdit()) {
      this.openCreate();
      this.form.patchValue({ customerId: this.customerId });
    }
  }

  load(): void {
    this.loading.set(true);
    this.api.listBookings({ page: this.page, search: this.search, customerId: this.customerId }).subscribe({
      next: (result) => {
        this.items = result.items;
        this.total = result.total;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load bookings.');
      },
    });
  }

  openCreate(): void {
    this.editing = null;
    this.form.reset({
      offeringId: '',
      customerId: this.customerId,
      bookingStartDate: new Date().toISOString().slice(0, 10),
      bookingEndDate: '',
      securityPaid: '0.00',
    });
    this.modalOpen.set(true);
  }

  openEdit(row: Booking): void {
    this.editing = row;
    this.form.patchValue({
      offeringId: row.offeringId ?? '',
      customerId: row.customerId ?? '',
      bookingStartDate: row.bookingStartDate,
      bookingEndDate: row.bookingEndDate,
      securityPaid: row.securityPaid,
    });
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
      .saveBooking({
        id: this.editing?.id,
        offeringId: value.offeringId || null,
        customerId: value.customerId || null,
        bookingStartDate: value.bookingStartDate,
        bookingEndDate: value.bookingEndDate,
        securityPaid: parseMoneyInput(value.securityPaid),
      })
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.modalOpen.set(false);
          this.toast.success(this.editing ? 'Booking updated' : 'Booking created');
          this.load();
        },
        error: (err) => {
          this.saving.set(false);
          this.toast.error('Save failed', err.message);
        },
      });
  }
}
