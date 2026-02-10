import { test, expect } from '@playwright/test';

/**
 * Query Submission E2E Tests
 * Week 11: Full query workflow testing
 */

test.describe('Query Submission Flow', () => {
  
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.fill('input[name="apiKey"]', 'sk-ape-demo-12345678901234567890');
    await page.click('button[type="submit"]');
    await page.waitForURL('/dashboard');
  });

  test('should complete full query submission flow', async ({ page }) => {
    // Navigate to new query page
    await page.click('a:has-text("New Query")');
    await expect(page).toHaveURL('/dashboard/query/new');
    
    // Fill query
    const query = 'Calculate Sharpe ratio for AAPL from 2023-01-01 to 2023-12-31';
    await page.fill('textarea[name="query"]', query);
    
    // Submit
    await page.click('button:has-text("Submit Query")');
    
    // Should navigate to query status page
    await page.waitForURL(/\/dashboard\/query\/[a-f0-9-]+/);
    
    // Check pipeline status is shown
    await expect(page.locator('[data-testid="pipeline-status"]')).toBeVisible();
    
    // Wait for completion (up to 60 seconds)
    await page.waitForSelector('text=COMPLETED', { timeout: 60000 });
    
    // View results
    await page.click('button:has-text("View Results")');
    
    // Should show results page
    await expect(page).toHaveURL(/\/dashboard\/results\/[a-f0-9-]+/);
    await expect(page.locator('h2')).toContainText('Results');
  });

  test('should show disclaimer in results', async ({ page }) => {
    // Submit query
    await page.click('a:has-text("New Query")');
    await page.fill('textarea[name="query"]', 'Calculate correlation between SPY and QQQ');
    await page.click('button:has-text("Submit Query")');
    
    // Wait for completion
    await page.waitForURL(/\/dashboard\/query\/[a-f0-9-]+/);
    await page.waitForSelector('text=COMPLETED', { timeout: 60000 });
    
    // View results
    await page.click('button:has-text("View Results")');
    
    // Check disclaimer is present
    await expect(page.locator('text=informational purposes only')).toBeVisible();
    await expect(page.locator('text=not be considered financial advice')).toBeVisible();
  });

  test('should show data source attribution', async ({ page }) => {
    // Submit and complete query
    await page.click('a:has-text("New Query")');
    await page.fill('textarea[name="query"]', 'Calculate volatility for MSFT');
    await page.click('button:has-text("Submit Query")');
    
    await page.waitForURL(/\/dashboard\/query\/[a-f0-9-]+/);
    await page.waitForSelector('text=COMPLETED', { timeout: 60000 });
    await page.click('button:has-text("View Results")');
    
    // Check data source is shown
    await expect(page.locator('text=Data Source')).toBeVisible();
    await expect(page.locator('text=yfinance')).toBeVisible();
  });

  test('should validate empty query', async ({ page }) => {
    await page.click('a:has-text("New Query")');
    
    // Try to submit empty query
    await page.click('button:has-text("Submit Query")');
    
    // Should show validation error
    await expect(page.locator('text=Query cannot be empty')).toBeVisible();
    
    // Should stay on same page
    await expect(page).toHaveURL('/dashboard/query/new');
  });

  test('should validate query too short', async ({ page }) => {
    await page.click('a:has-text("New Query")');
    
    // Fill short query
    await page.fill('textarea[name="query"]', 'Hi');
    await page.click('button:has-text("Submit Query")');
    
    // Should show validation error
    await expect(page.locator('text=Query must be at least')).toBeVisible();
  });

  test('should handle query error gracefully', async ({ page }) => {
    await page.click('a:has-text("New Query")');
    
    // Submit query with invalid ticker
    await page.fill('textarea[name="query"]', 'Calculate metrics for INVALID_TICKER_XYZ_12345');
    await page.click('button:has-text("Submit Query")');
    
    // Wait for error or completion
    await page.waitForSelector('text=ERROR, text=COMPLETED', { timeout: 60000 });
    
    // Should show error state or message
    const errorVisible = await page.locator('text=ERROR').isVisible().catch(() => false);
    const errorMessageVisible = await page.locator('text=error, text=Error').isVisible().catch(() => false);
    
    expect(errorVisible || errorMessageVisible).toBeTruthy();
  });

  test('should show real-time status updates', async ({ page }) => {
    await page.click('a:has-text("New Query")');
    await page.fill('textarea[name="query"]', 'Calculate beta for SPY against VOO');
    await page.click('button:has-text("Submit Query")');
    
    await page.waitForURL(/\/dashboard\/query\/[a-f0-9-]+/);
    
    // Check status progression
    const statuses = ['PLAN', 'FETCH', 'VEE', 'GATE', 'DEBATE', 'COMPLETED'];
    for (const status of statuses) {
      await expect(page.locator(`text=${status}`)).toBeVisible({ timeout: 30000 });
    }
  });
});
