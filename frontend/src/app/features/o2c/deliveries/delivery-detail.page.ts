import { Component, OnInit, computed, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { DocumentTrailComponent } from '../../../shared/components/document-trail/document-trail.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { O2cBannerComponent } from '../components/o2c-banner.component';
import { Delivery, SalesInvoice } from '../models/o2c.model';
import { O2cApiService } from '../services/o2c-api.service';

@Component({
  selector: 'app-delivery-detail-page',
  standalone: true,
  imports: [RouterLink, PageHeaderComponent, O2cBannerComponent, DocumentTrailComponent, StatusBadgeComponent, EmptyStateComponent],
  templateUrl: './delivery-detail.page.html',
})
export class DeliveryDetailPage implements OnInit {
  private readonly api = inject(O2cApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly auth = inject(AuthService);
  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  record: Delivery | null = null;
  invoices: SalesInvoice[] = [];

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    forkJoin({ record: this.api.getDelivery(id), invoices: this.api.listSalesInvoices({ pageSize: 50 }) }).subscribe(
      (data) => {
        this.record = data.record;
        this.invoices = data.invoices.items.filter((row) => row.deliveryId === id);
      },
    );
  }
}
