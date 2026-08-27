import { Component, OnInit, computed, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { DocumentTrailComponent } from '../../../shared/components/document-trail/document-trail.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { Booking, LegacyInvoice } from '../../o2c/models/o2c.model';
import { O2cApiService } from '../../o2c/services/o2c-api.service';
import { ExistingSalesBannerComponent } from '../components/existing-sales-banner.component';

@Component({
  selector: 'app-booking-detail-page',
  standalone: true,
  imports: [RouterLink, PageHeaderComponent, ExistingSalesBannerComponent, DocumentTrailComponent, EmptyStateComponent, InrPipe],
  templateUrl: './booking-detail.page.html',
})
export class BookingDetailPage implements OnInit {
  private readonly api = inject(O2cApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly auth = inject(AuthService);
  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  record: Booking | null = null;
  invoices: LegacyInvoice[] = [];

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    forkJoin({ record: this.api.getBooking(id), invoices: this.api.listInvoices({ pageSize: 50 }) }).subscribe((data) => {
      this.record = data.record;
      this.invoices = data.invoices.items.filter((row) => row.bookingId === id);
    });
  }
}
