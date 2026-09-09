import { createServer } from 'vite';

const server = await createServer({
  configFile: 'vite.config.js',
  mode: 'development',
});

await server.listen();
server.printUrls();

