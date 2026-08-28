import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { parseMoneyInput } from '../../../core/utils/money.util';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { FilterBarComponent, FilterBarSelect, FilterBarState } from '../../../shared/components/filter-bar/filter-bar.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { Booking, Customer, LegacyInvoice } from '../../o2c/models/o2c.model';
import { O2cApiService } from '../../o2c/services/o2c-api.service';
import { ExistingSalesBannerComponent } from '../components/existing-sales-banner.component';

@Component({
  selector: 'app-invoice-list-page',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    PageHeaderComponent,
    ExistingSalesBannerComponent,
    FilterBarComponent,
    StatusBadgeComponent,
    PaginationComponent,
    ModalComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
    InrPipe,
  ],
  templateUrl: './invoice-list.page.html',
})
export class InvoiceListPage implements OnInit {
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
  items: LegacyInvoice[] = [];
  customers: Customer[] = [];
  bookings: Booking[] = [];
  total = 0;
  page = 1;
  search = '';
  status = '';
  customerId = '';
  editing: LegacyInvoice | null = null;

  readonly form = this.fb.nonNullable.group({
    invoiceNumber: ['', Validators.required],
    customerId: [''],
    bookingId: [''],
    invoiceRaisedDate: [new Date().toISOString().slice(0, 10), Validators.required],
    securityAmountDeposited: ['0.00', Validators.required],
    invoiceAmount: ['0.00', Validators.required],
    isGstInvoice: [false],
    gstAmount: ['0.00', Validators.required],
  });

  ngOnInit(): void {
    const params = this.route.snapshot.queryParamMap;
    this.customerId = params.get('customerId') ?? '';
    this.api.listCustomers({ pageSize: 100 }).subscribe((result) => (this.customers = result.items));
    this.api.listBookings({ pageSize: 100 }).subscribe((result) => {
      this.bookings = result.items;
      if (params.get('create') === '1' && this.canEdit()) {
        this.openCreate();
        const bookingId = params.get('bookingId') ?? '';
        const booking = this.bookings.find((row) => row.id === bookingId);
        this.form.patchValue({
          customerId: params.get('customerId') ?? booking?.customerId ?? '',
          bookingId,
          securityAmountDeposited: booking?.securityPaid ?? '0.00',
        });
      }
    });
    this.load();
    this.form.controls.bookingId.valueChanges.subscribe((bookingId) => {
      const booking = this.bookings.find((row) => row.id === bookingId);
      if (booking) {
        this.form.patchValue(
          { customerId: booking.customerId ?? '', securityAmountDeposited: booking.securityPaid },
          { emitEvent: false },
        );
      }
    });
  }

  load(): void {
    this.loading.set(true);
    this.api
      .listInvoices({ page: this.page, search: this.search, status: this.status, customerId: this.customerId })
      .subscribe({
        next: (result) => {
          this.items = result.items;
          this.total = result.total;
          this.loading.set(false);
        },
        error: () => {
          this.loading.set(false);
          this.error.set('Unable to load invoices.');
        },
      });
  }

  get filterSelects(): FilterBarSelect[] {
    return [
      {
        key: 'customer',
        label: 'Customer',
        blankLabel: 'All customers',
        value: this.customerId,
        options: this.customers.map((customer) => ({ value: customer.id, label: customer.name })),
      },
      {
        key: 'status',
        label: 'Status',
        blankLabel: 'All statuses',
        value: this.status,
        options: [
          { value: 'pending', label: 'Pending' },
          { value: 'partially_paid', label: 'Partially paid' },
          { value: 'paid', label: 'Paid' },
        ],
      },
    ];
  }

  onFilters(state: FilterBarState): void {
    this.search = state.search;
    this.customerId = state.values['customer'] ?? '';
    this.status = state.values['status'] ?? '';
    this.page = 1;
    this.load();
  }

  outstanding(row: LegacyInvoice): string {
    return row.outstanding ?? row.invoiceAmount;
  }

  openCreate(): void {
    this.editing = null;
    this.form.reset({
      invoiceNumber: `SI-${new Date().getFullYear()}-${String(this.total + 1).padStart(4, '0')}`,
      customerId: this.customerId,
      bookingId: '',
      invoiceRaisedDate: new Date().toISOString().slice(0, 10),
      securityAmountDeposited: '0.00',
      invoiceAmount: '0.00',
      isGstInvoice: false,
      gstAmount: '0.00',
    });
    this.modalOpen.set(true);
  }

  openEdit(_row: LegacyInvoice): void {
    this.toast.error('Updating an invoice is not supported by the API yet.');
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    this.saving.set(true);
    this.api
      .saveInvoice({
        id: this.editing?.id,
        invoiceNumber: value.invoiceNumber,
        customerId: value.customerId || null,
        bookingId: value.bookingId || null,
        planId: null,
        invoiceRaisedDate: value.invoiceRaisedDate,
        securityAmountDeposited: parseMoneyInput(value.securityAmountDeposited),
        invoiceAmount: parseMoneyInput(value.invoiceAmount),
        isGstInvoice: value.isGstInvoice,
        gstAmount: parseMoneyInput(value.gstAmount),
      })
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.modalOpen.set(false);
          this.toast.success(this.editing ? 'Invoice updated' : 'Invoice recorded');
          this.load();
        },
        error: (err) => {
          this.saving.set(false);
          this.toast.error('Save failed', err.message);
        },
      });
  }
}
