import { test, expect } from '@playwright/test'

test('SSR authentication, hydration, thumbnails, model tasks and mobile layout', async ({ page, context }, testInfo) => {
 const errors: string[] = [];
 page.on('pageerror', error => errors.push(error.message));
 const requests: string[] = [];
 page.on('request', request => requests.push(request.url()));
 await page.goto('http://127.0.0.1:3900/');
 await expect(page).toHaveURL(/login/);
 await page.locator('input[type=password]').fill('smoke-test-password');
 await page.getByRole('button', {name:/登录/}).click();
 await expect(page).toHaveURL('http://127.0.0.1:3900/');
 await expect(page.locator('.card-item')).toHaveCount(10);
 requests.length=0;
 await page.goto('http://127.0.0.1:3900/');
 await expect(page.locator('.coverimg').first()).toBeVisible();
 await page.waitForLoadState('networkidle');
 if(requests.some(url => url.includes('/api/index'))) throw new Error('Duplicate client hydration fetch');
 const dimensions=await page.locator('.coverimg').first().evaluate((img: HTMLImageElement) => ({natural:img.naturalWidth, loading:img.loading}));
 const coverSource = await page.locator('.coverimg').first().getAttribute('src');
 expect(new URL(coverSource!, page.url()).searchParams.get('referer')).toMatch(/^https:\/\/example\.com\//);
 if(!dimensions.natural || dimensions.natural>960 || dimensions.loading!=='eager') throw new Error(JSON.stringify(dimensions));
 await page.locator('.coverimg').first().click();
 await expect(page.locator('.img-modal-overlay')).toBeVisible();
 await page.locator('.img-modal-overlay').click({position:{x:5,y:5}});
 await page.goto('http://127.0.0.1:3900/tagit');
 await page.getByRole('button',{name:'喜欢',exact:true}).click();
 await expect(page.locator('.card-item')).toHaveCount(10);
 await page.goto('http://127.0.0.1:3900/search');
 await page.getByRole('combobox', { name: '类型标签' }).click();
 await expect(page.getByRole('option', { name: 'Smoke genre' })).toBeVisible();
 await page.goto('http://127.0.0.1:3900/model');
 const submitted=page.waitForResponse(res=>res.url().endsWith('/api/do-training')&&res.status()===202);
 await page.getByRole('button',{name:'开始训练'}).click();
 const job=(await (await submitted).json()).job;
 await expect(page.getByRole('button',{name:'开始训练'})).toBeEnabled({timeout:20000});
 const state=await (await context.request.get('http://127.0.0.1:3900/api/jobs/'+job.id)).json();
 if(state.job.state!=='succeeded') throw new Error(JSON.stringify(state));
 await page.screenshot({path:testInfo.outputPath('model.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});
 await page.goto('http://127.0.0.1:3900/');
 await expect(page.locator('.coverimg').first()).toBeVisible();
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
 if(overflow) throw new Error('Mobile horizontal overflow');
 await page.screenshot({path:testInfo.outputPath('mobile.png'),fullPage:false});
 if(errors.length) throw new Error(errors.join('\n'));
 console.log(JSON.stringify({browser:'Chrome',hydration:'no duplicate initial data fetch',thumbnails:dimensions,taskUI:'passed',mobile:'390px, no overflow',pageErrors:errors}));

})
