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
import { Quotation, SalesOrder } from '../models/o2c.model';
import { O2cApiService } from '../services/o2c-api.service';

@Component({
  selector: 'app-quotation-detail-page',
  standalone: true,
  imports: [RouterLink, PageHeaderComponent, O2cBannerComponent, DocumentTrailComponent, StatusBadgeComponent, EmptyStateComponent, InrPipe],
  templateUrl: './quotation-detail.page.html',
})
export class QuotationDetailPage implements OnInit {
  private readonly api = inject(O2cApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly auth = inject(AuthService);
  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  record: Quotation | null = null;
  orders: SalesOrder[] = [];

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    forkJoin({ record: this.api.getQuotation(id), orders: this.api.listSalesOrders({ pageSize: 50 }) }).subscribe((data) => {
      this.record = data.record;
      this.orders = data.orders.items.filter((row) => row.quotationId === id);
    });
  }
}
