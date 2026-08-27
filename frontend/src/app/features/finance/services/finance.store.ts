import { Injectable, inject } from '@angular/core';

import { AuditStore } from '../../../core/audit/audit.store';
import { AuthService } from '../../../core/auth/auth.service';
import { addMoney, subtractMoney } from '../../../core/utils/money.util';
import {
  Category,
  DocumentMeta,
  Expense,
  FinanceAccount,
  FinanceQuery,
  FinanceState,
  FinanceTransaction,
  Offering,
  PageResult,
  Product,
  Subcategory,
} from '../models/finance.model';
import { DEMO_ORGANIZATION_ID } from '../../../core/seed/ids';
import { createInitialFinanceState } from '../seed/finance.seed';

@Injectable({ providedIn: 'root' })
export class FinanceStore {
  private readonly auth = inject(AuthService);
  private readonly audit = inject(AuditStore);

  private key(): string {
    return `bfms_finance_${this.auth.session()?.organizationId ?? DEMO_ORGANIZATION_ID}`;
  }

  load(): FinanceState {
    const raw = localStorage.getItem(this.key());
    if (!raw) {
      const initial = createInitialFinanceState();
      this.save(initial);
      return initial;
    }
    try {
      return JSON.parse(raw) as FinanceState;
    } catch {
      const initial = createInitialFinanceState();
      this.save(initial);
      return initial;
    }
  }

  save(state: FinanceState): void {
    localStorage.setItem(this.key(), JSON.stringify(state));
  }

  nextId(prefix: string): string {
    return `${prefix}-${Date.now().toString(36)}`;
  }

  page<T>(items: T[], query: FinanceQuery, searchFields: (item: T) => string): PageResult<T> {
    const page = query.page ?? 1;
    const pageSize = query.pageSize ?? 10;
    const search = (query.search ?? '').trim().toLowerCase();
    const filtered = items.filter((item) => {
      const row = item as T & {
        status?: string;
        vendorId?: string | null;
        categoryId?: string | null;
        accountId?: string;
        expenseDate?: string;
        transactionDate?: string;
        isActive?: boolean;
      };
      const date = row.expenseDate ?? row.transactionDate ?? '';
      const matchesSearch = !search || searchFields(item).toLowerCase().includes(search);
      const matchesStatus =
        !query.status ||
        row.status === query.status ||
        (query.status === 'active' && row.isActive === true) ||
        (query.status === 'inactive' && row.isActive === false);
      const matchesVendor = !query.vendorId || row.vendorId === query.vendorId;
      const matchesCategory = !query.categoryId || row.categoryId === query.categoryId;
      const matchesAccount = !query.accountId || row.accountId === query.accountId;
      const matchesFrom = !query.dateFrom || date >= query.dateFrom;
      const matchesTo = !query.dateTo || date <= query.dateTo;
      return matchesSearch && matchesStatus && matchesVendor && matchesCategory && matchesAccount && matchesFrom && matchesTo;
    });
    const start = (page - 1) * pageSize;
    return { items: filtered.slice(start, start + pageSize), total: filtered.length, page, pageSize };
  }

  write<T extends { id: string }>(items: T[], record: T): void {
    const index = items.findIndex((row) => row.id === record.id);
    if (index >= 0) {
      items[index] = record;
    } else {
      items.unshift(record);
    }
  }

  appendAudit(entityName: string, entityId: string, action: string, summary: string): void {
    this.audit.record(entityName, entityId, action, summary);
  }

  upsertProduct(record: Product): Product {
    const state = this.load();
    const existed = state.products.some((row) => row.id === record.id);
    this.write(state.products, record);
    this.save(state);
    this.appendAudit('product', record.id, existed ? 'update' : 'create', `${existed ? 'Updated' : 'Created'} product ${record.name}`);
    return record;
  }

  upsertCategory(record: Category): Category {
    const state = this.load();
    const existed = state.categories.some((row) => row.id === record.id);
    this.write(state.categories, record);
    state.subcategories.forEach((row) => {
      if (row.categoryId === record.id) {
        row.categoryName = record.name;
      }
    });
    this.save(state);
    this.appendAudit('category', record.id, existed ? 'update' : 'create', `${existed ? 'Updated' : 'Created'} category ${record.name}`);
    return record;
  }

  upsertSubcategory(record: Subcategory): Subcategory {
    const state = this.load();
    const existed = state.subcategories.some((row) => row.id === record.id);
    record.categoryName = state.categories.find((row) => row.id === record.categoryId)?.name ?? record.categoryName;
    this.write(state.subcategories, record);
    this.save(state);
    this.appendAudit('subcategory', record.id, existed ? 'update' : 'create', `${existed ? 'Updated' : 'Created'} subcategory ${record.name}`);
    return record;
  }

  upsertOffering(record: Offering): Offering {
    const state = this.load();
    const existed = state.offerings.some((row) => row.id === record.id);
    record.productName = state.products.find((row) => row.id === record.productId)?.name ?? '';
    this.write(state.offerings, record);
    this.save(state);
    this.appendAudit('income_offering', record.id, existed ? 'update' : 'create', `${existed ? 'Updated' : 'Created'} offering ${record.name}`);
    return record;
  }

  upsertExpense(record: Expense): Expense {
    const state = this.load();
    const existed = state.expenses.some((row) => row.id === record.id);
    this.write(state.expenses, record);
    this.save(state);
    this.appendAudit('expense', record.id, existed ? 'update' : 'create', `${existed ? 'Updated' : 'Recorded'} expense ${record.productServiceName || record.id}`);
    return record;
  }

  upsertAccount(record: FinanceAccount): FinanceAccount {
    const state = this.load();
    const existed = state.accounts.some((row) => row.id === record.id);
    this.write(state.accounts, record);
    this.save(state);
    this.appendAudit('finance_account', record.id, existed ? 'update' : 'create', `${existed ? 'Updated' : 'Opened'} account ${record.name}`);
    return record;
  }

  upsertTransaction(record: FinanceTransaction): FinanceTransaction {
    const state = this.load();
    const previous = state.transactions.find((row) => row.id === record.id);
    if (previous) {
      this.applyBalance(state, previous, -1);
    }
    const account = state.accounts.find((row) => row.id === record.accountId);
    if (!account) {
      throw new Error('Account is required.');
    }
    record.accountName = account.name;
    this.applyBalance(state, record, 1);
    this.write(state.transactions, record);
    this.save(state);
    this.appendAudit(
      'finance_transaction',
      record.id,
      previous ? 'update' : 'create',
      `Posted ${record.transactionType} ${record.amount} to ${record.accountName}`,
    );
    return record;
  }

  setReconciled(id: string, reconciled: boolean): FinanceTransaction {
    const state = this.load();
    const record = state.transactions.find((row) => row.id === id);
    if (!record) {
      throw new Error('Transaction not found.');
    }
    record.reconciled = reconciled;
    this.save(state);
    this.appendAudit('finance_transaction', record.id, 'update', `${reconciled ? 'Reconciled' : 'Unreconciled'} ${record.accountName} ${record.amount}`);
    return record;
  }

  upsertDocument(record: DocumentMeta): DocumentMeta {
    const state = this.load();
    const existed = state.documents.some((row) => row.id === record.id);
    this.write(state.documents, record);
    this.save(state);
    this.appendAudit('document', record.id, existed ? 'update' : 'create', `${existed ? 'Updated' : 'Stored'} document ${record.fileName}`);
    return record;
  }

  private applyBalance(state: FinanceState, tx: FinanceTransaction, sign: 1 | -1): void {
    const account = state.accounts.find((row) => row.id === tx.accountId);
    if (!account) {
      throw new Error('Account not found.');
    }
    if (tx.transactionType === 'credit') {
      account.balance = sign === 1 ? addMoney(account.balance, tx.amount) : subtractMoney(account.balance, tx.amount);
    } else {
      account.balance = sign === 1 ? subtractMoney(account.balance, tx.amount) : addMoney(account.balance, tx.amount);
    }
  }
}
