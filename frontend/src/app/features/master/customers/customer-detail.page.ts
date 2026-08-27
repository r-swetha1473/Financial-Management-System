import { Component, OnInit, computed, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { DocumentTrailComponent } from '../../../shared/components/document-trail/document-trail.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { O2cBannerComponent } from '../../o2c/components/o2c-banner.component';
import { Booking, Customer, InvoiceReceipt, LegacyInvoice, Quotation, SalesInvoice } from '../../o2c/models/o2c.model';
import { O2cApiService } from '../../o2c/services/o2c-api.service';

@Component({
  selector: 'app-customer-detail-page',
  standalone: true,
  imports: [RouterLink, PageHeaderComponent, O2cBannerComponent, DocumentTrailComponent, StatusBadgeComponent, EmptyStateComponent],
  templateUrl: './customer-detail.page.html',
})
export class CustomerDetailPage implements OnInit {
  private readonly api = inject(O2cApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly auth = inject(AuthService);
  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  customer: Customer | null = null;
  quotations: Quotation[] = [];
  invoices: SalesInvoice[] = [];
  bookings: Booking[] = [];
  legacyInvoices: LegacyInvoice[] = [];
  receipts: InvoiceReceipt[] = [];

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    forkJoin({
      customer: this.api.getCustomer(id),
      quotations: this.api.listQuotations({ customerId: id, pageSize: 20 }),
      invoices: this.api.listSalesInvoices({ customerId: id, pageSize: 20 }),
      bookings: this.api.listBookings({ customerId: id, pageSize: 20 }),
      legacyInvoices: this.api.listInvoices({ customerId: id, pageSize: 20 }),
      receipts: this.api.listReceipts({ customerId: id, pageSize: 20 }),
    }).subscribe((data) => {
      this.customer = data.customer;
      this.quotations = data.quotations.items;
      this.invoices = data.invoices.items;
      this.bookings = data.bookings.items;
      this.legacyInvoices = data.legacyInvoices.items;
      this.receipts = data.receipts.items;
    });
  }
}
