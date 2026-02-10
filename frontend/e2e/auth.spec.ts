import { test, expect } from '@playwright/test';

/**
 * Authentication E2E Tests
 * Week 11: User login and API key validation
 */

test.describe('Authentication Flow', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('should display login form', async ({ page }) => {
    // Check form elements
    await expect(page.locator('input[name="apiKey"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
    await expect(page.locator('text=Login')).toBeVisible();
  });

  test('should login with valid API key', async ({ page }) => {
    // Fill in demo API key
    await page.fill('input[name="apiKey"]', 'sk-ape-demo-12345678901234567890');
    
    // Submit form
    await page.click('button[type="submit"]');
    
    // Should redirect to dashboard
    await expect(page).toHaveURL('/dashboard');
    
    // Should show dashboard content
    await expect(page.locator('h1')).toContainText('Dashboard');
  });

  test('should show error for invalid API key', async ({ page }) => {
    // Fill in invalid key
    await page.fill('input[name="apiKey"]', 'invalid-key');
    
    // Submit form
    await page.click('button[type="submit"]');
    
    // Should show error
    await expect(page.locator('text=Invalid API key')).toBeVisible();
    
    // Should stay on login page
    await expect(page).toHaveURL('/login');
  });

  test('should show error for empty API key', async ({ page }) => {
    // Submit without filling
    await page.click('button[type="submit"]');
    
    // Should show validation error
    await expect(page.locator('text=API key is required')).toBeVisible();
  });

  test('should persist login state', async ({ page, context }) => {
    // Login
    await page.fill('input[name="apiKey"]', 'sk-ape-demo-12345678901234567890');
    await page.click('button[type="submit"]');
    
    // Wait for navigation
    await page.waitForURL('/dashboard');
    
    // Open new tab
    const newPage = await context.newPage();
    await newPage.goto('/dashboard');
    
    // Should still be logged in
    await expect(newPage.locator('h1')).toContainText('Dashboard');
  });

  test('should logout successfully', async ({ page }) => {
    // Login first
    await page.fill('input[name="apiKey"]', 'sk-ape-demo-12345678901234567890');
    await page.click('button[type="submit"]');
    await page.waitForURL('/dashboard');
    
    // Click logout
    await page.click('text=Logout');
    
    // Should redirect to login
    await expect(page).toHaveURL('/login');
    
    // Try to access dashboard - should redirect back to login
    await page.goto('/dashboard');
    await expect(page).toHaveURL('/login');
  });
});
