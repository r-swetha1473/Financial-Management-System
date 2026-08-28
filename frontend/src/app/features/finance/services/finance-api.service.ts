import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';

import { ApiClientService, ApiError } from '../../../core/api/api-client.service';
import { ReportViewModel } from './report.service';
import {
  Category,
  DocumentMeta,
  Expense,
  FinanceAccount,
  FinanceQuery,
  FinanceTransaction,
  GstSummary,
  IncomeRecord,
  Offering,
  PageResult,
  Product,
  ReconciliationNote,
  Subcategory,
} from '../models/finance.model';

const unsupportedUpdate = (entity: string): ApiError => ({
  code: '501',
  message: `Updating ${entity} is not supported by the API yet.`,
});

@Injectable({ providedIn: 'root' })
export class FinanceApiService {
  private readonly api = inject(ApiClientService);

  listProducts(query: FinanceQuery = {}): Observable<PageResult<Product>> {
    return this.api.getPaginated<Product>('/products', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
      search: query.search,
      status: query.status,
    });
  }
  getProduct(id: string): Observable<Product | null> {
    return this.api.get<Product>(`/products/${id}`);
  }
  saveProduct(payload: Omit<Product, 'id' | 'organizationId' | 'createdAt'> & { id?: string }): Observable<Product> {
    if (payload.id) {
      return throwError(() => unsupportedUpdate('a product'));
    }
    return this.api.post<Product>('/products', {
      name: payload.name,
      vinNumber: payload.vinNumber || null,
      model: payload.model || null,
      batteryType: payload.batteryType || null,
      bodyColor: payload.bodyColor || null,
      status: payload.status,
    });
  }

  listCategories(query: FinanceQuery = {}): Observable<PageResult<Category>> {
    return this.api.getPaginated<Category>('/categories', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
    });
  }
  saveCategory(payload: Omit<Category, 'id' | 'organizationId' | 'createdAt'> & { id?: string }): Observable<Category> {
    if (payload.id) {
      return throwError(() => unsupportedUpdate('a category'));
    }
    return this.api.post<Category>('/categories', {
      name: payload.name,
      description: payload.description || null,
      isActive: payload.isActive,
    });
  }

  listSubcategories(query: FinanceQuery = {}): Observable<PageResult<Subcategory>> {
    return this.api.getPaginated<Subcategory>('/subcategories', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
      category_id: query.categoryId,
    });
  }
  saveSubcategory(
    payload: Omit<Subcategory, 'id' | 'organizationId' | 'createdAt' | 'categoryName'> & { id?: string },
  ): Observable<Subcategory> {
    if (payload.id) {
      return throwError(() => unsupportedUpdate('a subcategory'));
    }
    return this.api.post<Subcategory>('/subcategories', {
      categoryId: payload.categoryId,
      name: payload.name,
      description: payload.description || null,
      isActive: payload.isActive,
    });
  }

  listOfferings(query: FinanceQuery = {}): Observable<PageResult<Offering>> {
    return this.api.getPaginated<Offering>('/offerings', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
    });
  }
  saveOffering(
    payload: Omit<Offering, 'id' | 'organizationId' | 'createdAt' | 'productName'> & { id?: string },
  ): Observable<Offering> {
    if (payload.id) {
      return throwError(() => unsupportedUpdate('a service offering'));
    }
    return this.api.post<Offering>('/offerings', {
      name: payload.name,
      productId: payload.productId || null,
      description: payload.description || null,
      amount: payload.amount,
      isActive: payload.isActive,
    });
  }

  listExpenses(query: FinanceQuery = {}): Observable<PageResult<Expense>> {
    return this.api.getPaginated<Expense>('/finance/expenses', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
    });
  }
  getExpense(id: string): Observable<Expense | null> {
    return this.api.get<Expense>(`/finance/expenses/${id}`);
  }
  saveExpense(
    payload: Omit<
      Expense,
      | 'id'
      | 'organizationId'
      | 'createdAt'
      | 'vendorName'
      | 'categoryName'
      | 'subcategoryName'
      | 'productName'
      | 'enteredBy'
    > & { id?: string; enteredBy?: string },
  ): Observable<Expense> {
    if (payload.id) {
      return throwError(() => unsupportedUpdate('an expense'));
    }
    return this.api.post<Expense>('/finance/expenses', {
      cost: payload.cost,
      expenseDate: payload.expenseDate,
      productServiceName: payload.productServiceName || null,
      vendorId: payload.vendorId || null,
    });
  }

  listIncome(query: FinanceQuery = {}): Observable<PageResult<IncomeRecord>> {
    return this.api.getPaginated<IncomeRecord>('/finance/income', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
    });
  }

  listAccounts(query: FinanceQuery = {}): Observable<PageResult<FinanceAccount>> {
    return this.api.getPaginated<FinanceAccount>('/finance/accounts', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
    });
  }

  listTransactions(query: FinanceQuery = {}): Observable<PageResult<FinanceTransaction>> {
    return this.api.getPaginated<FinanceTransaction>('/finance/transactions', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
      search: query.search,
      account_id: query.accountId,
    });
  }

  getGstSummary(dateFrom?: string, dateTo?: string): Observable<GstSummary> {
    return this.api.get<GstSummary>('/finance/gst/summary', {
      date_from: dateFrom,
      date_to: dateTo,
    });
  }

  getReconciliationNote(): Observable<ReconciliationNote> {
    return this.api.get<ReconciliationNote>('/finance/reconciliation/note');
  }
  saveReconciliationNote(note: string): Observable<ReconciliationNote> {
    return this.api.put<ReconciliationNote>('/finance/reconciliation/note', { note });
  }

  getReport(key: string): Observable<ReportViewModel> {
    return this.api.get<ReportViewModel>(`/reports/${key}`);
  }

  listDocuments(query: FinanceQuery = {}): Observable<PageResult<DocumentMeta>> {
    return this.api.getPaginated<DocumentMeta>('/documents', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
      search: query.search,
    });
  }
}
