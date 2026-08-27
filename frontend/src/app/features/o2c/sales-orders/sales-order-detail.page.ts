import { Component, OnInit, computed, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { DocumentTrailComponent } from '../../../shared/components/document-trail/document-trail.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { O2cBannerComponent } from '../components/o2c-banner.component';
import { Delivery, SalesInvoice, SalesOrder } from '../models/o2c.model';
import { O2cApiService } from '../services/o2c-api.service';

@Component({
  selector: 'app-sales-order-detail-page',
  standalone: true,
  imports: [
    RouterLink,
    PageHeaderComponent,
    O2cBannerComponent,
    DocumentTrailComponent,
    StatusBadgeComponent,
    EmptyStateComponent,
    InrPipe,
  ],
  templateUrl: './sales-order-detail.page.html',
})
export class SalesOrderDetailPage implements OnInit {
  private readonly api = inject(O2cApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly auth = inject(AuthService);
  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  record: SalesOrder | null = null;
  deliveries: Delivery[] = [];
  invoices: SalesInvoice[] = [];

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    forkJoin({
      record: this.api.getSalesOrder(id),
      deliveries: this.api.listDeliveries({ pageSize: 50 }),
      invoices: this.api.listSalesInvoices({ pageSize: 50 }),
    }).subscribe((data) => {
      this.record = data.record;
      this.deliveries = data.deliveries.items.filter((row) => row.salesOrderId === id);
      this.invoices = data.invoices.items.filter((row) => row.salesOrderId === id);
    });
  }
}
