import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { NAV_SECTIONS, O2C_WORKFLOW_STEPS } from '../../core/navigation/nav.config';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-o2c-overview-page',
  standalone: true,
  imports: [RouterLink, PageHeaderComponent],
  templateUrl: './o2c-overview.page.html',
})
export class O2cOverviewPage {
  readonly steps = O2C_WORKFLOW_STEPS;
  readonly items = [
    { label: 'Customers', route: '/master/customers' },
    ...(NAV_SECTIONS.find((section) => section.module === 'o2c')?.items ?? []),
  ];
}
