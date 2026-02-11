import { test, expect } from '@playwright/test';

/**
 * Multi-LLM Debate E2E Tests
 * Week 11: Full debate workflow testing with Bull/Bear/Arbiter
 */

test.describe('Multi-LLM Debate Flow', () => {

  test.beforeEach(async ({ page }) => {
    // Mock API health endpoint for login
    await page.route('**/api/health', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'healthy' })
      });
    });

    // Mock default successful debate response (can be overridden in specific tests)
    await page.route('**/api/analyze-debate', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          perspectives: {
            bull: {
              analysis: 'Strong growth potential with positive market momentum and increasing revenue.',
              confidence: 0.75,
              key_points: ['Revenue growth', 'Market position', 'Technical indicators'],
              provider: 'deepseek'
            },
            bear: {
              analysis: 'Significant risks including high valuation and regulatory concerns.',
              confidence: 0.65,
              key_points: ['High P/E ratio', 'Regulatory headwinds', 'Market volatility'],
              provider: 'anthropic'
            },
            arbiter: {
              analysis: 'Balanced view considering both growth potential and material risks.',
              confidence: 0.70,
              key_points: ['Growth vs risks', 'Reasonable valuation', 'Uncertain conditions'],
              provider: 'openai',
              recommendation: 'HOLD'
            }
          },
          synthesis: {
            recommendation: 'HOLD',
            overall_confidence: 0.70,
            risk_reward_ratio: '55/45'
          },
          metadata: {
            cost_usd: 0.002,
            latency_ms: 3500,
            timestamp: Date.now()
          }
        })
      });
    });

    // Login
    await page.goto('/login');
    await page.fill('input#apiKey', 'sk-ape-demo-12345678901234567890');
    await page.click('button[type="submit"]');
    await page.waitForURL('/dashboard');
  });

  test('should complete full debate analysis flow', async ({ page }) => {
    // Navigate to Multi-LLM Debate page
    await page.click('a:has-text("Multi-LLM Debate")');
    await expect(page).toHaveURL('/dashboard/debate');

    // Check page header (use more specific selector to avoid multiple h1 matches)
    await expect(page.locator('h1:has-text("Multi-LLM Debate")')).toBeVisible();
    await expect(page.locator('text=Get Bull, Bear, and Arbiter perspectives')).toBeVisible();

    // Fill query
    const query = 'Should I buy Tesla stock at current valuation?';
    await page.fill('textarea[id="query"]', query);

    // Submit debate
    await page.click('button:has-text("Run Multi-LLM Debate")');

    // Wait for results (up to 10 seconds)
    await expect(page.locator('text=Multi-LLM Debate Analysis')).toBeVisible({ timeout: 10000 });

    // Wait for results to be displayed
    await expect(page.locator('text=Multi-LLM Debate Analysis')).toBeVisible();

    // Check all three perspective cards are visible
    await expect(page.locator('.border-green-500\\/50')).toBeVisible(); // Bull card
    await expect(page.locator('.border-red-500\\/50')).toBeVisible(); // Bear card
    await expect(page.locator('.border-purple-500\\/50')).toBeVisible(); // Arbiter card

    // Check recommendation badge exists (BUY/HOLD/SELL)
    const badge = page.locator('text=/^(BUY|HOLD|SELL)$/').first();
    await expect(badge).toBeVisible();

    // Check confidence scores are displayed
    await expect(page.locator('text=Overall Confidence')).toBeVisible();
    await expect(page.locator('text=/%/')).toBeVisible();

    // Check risk/reward ratio
    await expect(page.locator('text=Risk/Reward Ratio')).toBeVisible();

    // Check metadata (cost and latency)
    await expect(page.locator('text=/\\$0\\.\\d{4}/')).toBeVisible(); // Cost like $0.0020
    await expect(page.locator('text=/\\d+\\.\\ds/')).toBeVisible(); // Latency like 3.5s
  });

  test('should display all three perspectives with content', async ({ page }) => {
    await page.goto('/dashboard/debate');

    // Submit query
    await page.fill('textarea[id="query"]', 'Analyze Microsoft stock fundamentals');
    await page.click('button:has-text("Run Multi-LLM Debate")');

    // Wait for results
    await page.waitForSelector('text=Multi-LLM Debate Analysis', { timeout: 10000 });

    // Check Bull perspective
    const bullCard = page.locator('.border-green-500\\/50');
    await expect(bullCard).toBeVisible();
    await expect(bullCard.locator('text=Optimistic Analysis')).toBeVisible();
    await expect(bullCard.locator('text=deepseek')).toBeVisible(); // Provider badge

    // Check Bear perspective
    const bearCard = page.locator('.border-red-500\\/50');
    await expect(bearCard).toBeVisible();
    await expect(bearCard.locator('text=Skeptical Analysis')).toBeVisible();
    await expect(bearCard.locator('text=anthropic')).toBeVisible(); // Provider badge

    // Check Arbiter perspective
    const arbiterCard = page.locator('.border-purple-500\\/50');
    await expect(arbiterCard).toBeVisible();
    await expect(arbiterCard.locator('text=Balanced Synthesis')).toBeVisible();
    await expect(arbiterCard.locator('text=openai')).toBeVisible(); // Provider badge
  });

  test('should load example query when clicked', async ({ page }) => {
    // Navigate to debate page from dashboard
    await page.click('a:has-text("Multi-LLM Debate")');
    await expect(page).toHaveURL('/dashboard/debate');

    // Click first example query button
    const exampleButton = page.locator('button:has-text("Should I buy Tesla stock?")');
    await exampleButton.click();

    // Check query textarea is filled
    const queryTextarea = page.locator('textarea[id="query"]');
    await expect(queryTextarea).toHaveValue(/Tesla/);

    // Check context textarea has JSON
    const contextTextarea = page.locator('textarea[id="context"]');
    const contextValue = await contextTextarea.inputValue();
    expect(contextValue).toContain('TSLA');
  });

  test('should validate empty query', async ({ page }) => {
    // Navigate happens in beforeEach, just use the page
    await page.goto('/dashboard/debate', { waitUntil: 'networkidle' });

    // Try to submit without query
    await page.click('button:has-text("Run Multi-LLM Debate")');

    // Should show validation error
    await expect(page.locator('text=Please enter a query')).toBeVisible();

    // Should not show results
    await expect(page.locator('text=Multi-LLM Debate Analysis')).not.toBeVisible();
  });

  test('should validate invalid JSON context', async ({ page }) => {
    await page.goto('/dashboard/debate');

    // Fill query
    await page.fill('textarea[id="query"]', 'Analyze Apple stock');

    // Fill invalid JSON context
    await page.fill('textarea[id="context"]', '{invalid json}');

    // Submit
    await page.click('button:has-text("Run Multi-LLM Debate")');

    // Should show validation error
    await expect(page.locator('text=Context must be valid JSON')).toBeVisible();
  });

  test('should submit with valid JSON context', async ({ page }) => {
    await page.goto('/dashboard/debate');

    // Fill query
    await page.fill('textarea[id="query"]', 'Analyze NVIDIA at this price point');

    // Fill valid JSON context
    const context = JSON.stringify({
      ticker: 'NVDA',
      price: 890.50,
      market_cap: '2.2T'
    });
    await page.fill('textarea[id="context"]', context);

    // Submit
    await page.click('button:has-text("Run Multi-LLM Debate")');

    // Wait for results
    await expect(page.locator('text=Multi-LLM Debate Analysis')).toBeVisible({ timeout: 10000 });

    // Should show results without error
    await expect(page.locator('text=/^(BUY|HOLD|SELL)$/').first()).toBeVisible();
  });

  test('should handle API error gracefully (missing packages)', async ({ page, context }) => {
    // Create new page to setup route before navigation
    const newPage = await context.newPage();

    // Mock API health for login
    await newPage.route('**/api/health', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'healthy' })
      });
    });

    // Mock API to return 501 error
    await newPage.route('**/api/analyze-debate', route => {
      route.fulfill({
        status: 501,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Missing packages' })
      });
    });

    // Login
    await newPage.goto('/login');
    await newPage.fill('input#apiKey', 'sk-ape-demo-12345678901234567890');
    await newPage.click('button[type="submit"]');
    await newPage.waitForURL('/dashboard');

    // Navigate to debate page
    await newPage.goto('/dashboard/debate');

    // Submit query
    await newPage.fill('textarea[id="query"]', 'Test query');
    await newPage.click('button:has-text("Run Multi-LLM Debate")');

    // Should show error message
    await expect(newPage.locator('text=requires additional packages')).toBeVisible();

    await newPage.close();
  });

  test('should handle API error gracefully (missing API keys)', async ({ page, context }) => {
    // Create new page to setup route before navigation
    const newPage = await context.newPage();

    // Mock API health for login
    await newPage.route('**/api/health', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'healthy' })
      });
    });

    // Mock API to return 500 error
    await newPage.route('**/api/analyze-debate', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'DEEPSEEK_API_KEY not found' })
      });
    });

    // Login
    await newPage.goto('/login');
    await newPage.fill('input#apiKey', 'sk-ape-demo-12345678901234567890');
    await newPage.click('button[type="submit"]');
    await newPage.waitForURL('/dashboard');

    // Navigate to debate page
    await newPage.goto('/dashboard/debate');

    // Submit query
    await newPage.fill('textarea[id="query"]', 'Test query');
    await newPage.click('button:has-text("Run Multi-LLM Debate")');

    // Should show error message with API key name
    await expect(newPage.locator('text=DEEPSEEK_API_KEY not found')).toBeVisible();

    await newPage.close();
  });

  test('should disable submit button while loading', async ({ page, context }) => {
    // Create new page to setup route before navigation
    const newPage = await context.newPage();

    // Mock API health for login
    await newPage.route('**/api/health', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'healthy' })
      });
    });

    // Override default mock with delayed response to catch loading state
    await newPage.route('**/api/analyze-debate', async route => {
      await new Promise(resolve => setTimeout(resolve, 500)); // 500ms delay
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          perspectives: {
            bull: {
              analysis: 'Quick bull analysis',
              confidence: 0.75,
              key_points: ['Point 1'],
              provider: 'deepseek'
            },
            bear: {
              analysis: 'Quick bear analysis',
              confidence: 0.65,
              key_points: ['Point 1'],
              provider: 'anthropic'
            },
            arbiter: {
              analysis: 'Quick arbiter analysis',
              confidence: 0.70,
              key_points: ['Point 1'],
              provider: 'openai',
              recommendation: 'HOLD'
            }
          },
          synthesis: {
            recommendation: 'HOLD',
            overall_confidence: 0.70,
            risk_reward_ratio: '50/50'
          },
          metadata: {
            cost_usd: 0.002,
            latency_ms: 500,
            timestamp: Date.now()
          }
        })
      });
    });

    // Login
    await newPage.goto('/login');
    await newPage.fill('input#apiKey', 'sk-ape-demo-12345678901234567890');
    await newPage.click('button[type="submit"]');
    await newPage.waitForURL('/dashboard');

    // Navigate to debate page
    await newPage.goto('/dashboard/debate');

    // Fill query
    await newPage.fill('textarea[id="query"]', 'Quick test query');

    // Get submit button
    const submitButton = newPage.locator('button:has-text("Run Multi-LLM Debate")');

    // Submit
    await submitButton.click();

    // Button should be disabled during loading
    await expect(submitButton).toBeDisabled({ timeout: 1000 });

    // After completion, button should be enabled again
    await newPage.waitForSelector('text=Multi-LLM Debate Analysis', { timeout: 10000 });
    await expect(submitButton).toBeEnabled();

    await newPage.close();
  });

  test('should clear previous results when submitting new query', async ({ page }) => {
    await page.goto('/dashboard/debate');

    // First submission
    await page.fill('textarea[id="query"]', 'First query about Apple');
    await page.click('button:has-text("Run Multi-LLM Debate")');
    await page.waitForSelector('text=Multi-LLM Debate Analysis', { timeout: 10000 });

    // Verify first results
    await expect(page.locator('text=Multi-LLM Debate Analysis')).toBeVisible();

    // Second submission
    await page.fill('textarea[id="query"]', 'Second query about Google');
    await page.click('button:has-text("Run Multi-LLM Debate")');

    // Should show new results (verifies results were cleared and reloaded)
    await page.waitForSelector('text=Multi-LLM Debate Analysis', { timeout: 10000 });
    await expect(page.locator('text=Multi-LLM Debate Analysis')).toBeVisible();
  });

  test('should show key points for each perspective', async ({ page }) => {
    await page.goto('/dashboard/debate');

    // Submit query
    await page.fill('textarea[id="query"]', 'Evaluate Amazon stock');
    await page.click('button:has-text("Run Multi-LLM Debate")');

    // Wait for results
    await page.waitForSelector('text=Multi-LLM Debate Analysis', { timeout: 10000 });

    // Each perspective card should have key points section
    // Check "Key Points:" text appears 3 times (one for each perspective)
    const keyPointsElements = page.locator('text=Key Points:');
    await expect(keyPointsElements).toHaveCount(3);
  });

  test('should show info section explaining how it works', async ({ page }) => {
    await page.goto('/dashboard/debate');

    // Info section should be visible before any submission
    await expect(page.locator('text=How Multi-LLM Debate Works')).toBeVisible();
    await expect(page.locator('text=Parallel Execution')).toBeVisible();
    await expect(page.locator('text=Three Perspectives')).toBeVisible();
    await expect(page.locator('text=Cost & Speed')).toBeVisible();

    // Submit to verify info stays visible after results
    await page.fill('textarea[id="query"]', 'Test query');
    await page.click('button:has-text("Run Multi-LLM Debate")');
    await page.waitForSelector('text=Multi-LLM Debate Analysis', { timeout: 10000 });

    // Info should still be visible
    await expect(page.locator('text=How Multi-LLM Debate Works')).toBeVisible();
  });

  test('should render different recommendation types correctly', async ({ page }) => {
    // Test with mock data for different recommendations
    const recommendations = ['BUY', 'HOLD', 'SELL'];

    for (const rec of recommendations) {
      // Mock API with specific recommendation
      await page.route('**/api/analyze-debate', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            perspectives: {
              bull: {
                analysis: 'Bullish analysis',
                confidence: 0.75,
                key_points: ['Point 1'],
                provider: 'deepseek'
              },
              bear: {
                analysis: 'Bearish analysis',
                confidence: 0.65,
                key_points: ['Point 1'],
                provider: 'anthropic'
              },
              arbiter: {
                analysis: 'Balanced analysis',
                confidence: 0.70,
                key_points: ['Point 1'],
                provider: 'openai',
                recommendation: rec
              }
            },
            synthesis: {
              recommendation: rec,
              overall_confidence: 0.70,
              risk_reward_ratio: '50/50'
            },
            metadata: {
              cost_usd: 0.002,
              latency_ms: 3500,
              timestamp: Date.now()
            }
          })
        });
      });

      await page.goto('/dashboard/debate');
      await page.fill('textarea[id="query"]', `Test ${rec} recommendation`);
      await page.click('button:has-text("Run Multi-LLM Debate")');

      // Check recommendation badge
      await expect(page.locator(`text=/^${rec}$/`).first()).toBeVisible({ timeout: 5000 });

      // Unroute for next iteration
      await page.unroute('**/api/analyze-debate');
    }
  });
});
