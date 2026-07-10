import { Dataset, PlaywrightCrawler } from 'crawlee';

const crawler = new PlaywrightCrawler({
    maxRequestsPerCrawl: 10,

    async requestHandler({ request, page, enqueueLinks, log }) {
        const title = await page.title();
        log.info(`Title of ${request.loadedUrl} is '${title}'`);

        await Dataset.pushData({ title, url: request.loadedUrl });
        await enqueueLinks();
    },
});

await crawler.run(['https://crawlee.dev']);
