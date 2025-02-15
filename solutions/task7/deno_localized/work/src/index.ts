console.debug = ()=>{} // stop debug logging for main app
;
// @deno-types="npm:@types/express"
import express from 'express';
// @deno-types="npm:@types/body-parser"
import bodyParser from 'body-parser';
import { connectToDatabase, closeDatabaseConnection, aggregateLocationEvents } from './mongodb.ts';
import { logger } from './logger.ts';
import { registerRoutes } from './routes.ts';
const app = express();
const port = 3000;
const maintenanceInterval = parseInt('300000', 10); // default to 5 minutes
const uri = 'mongodb://127.0.0.1:27017';
const db = 'test';
app.use(bodyParser.json());
app.use(bodyParser.raw({
  type: 'application/msgpack'
}));
registerRoutes(app);
let server;
connectToDatabase(uri, db).then(()=>{
  server = app.listen(port, ()=>{
    logger.info(`Server is running on port ${port}`);
  });
  setInterval(async ()=>{
    try {
      await aggregateLocationEvents();
      logger.info('Maintenance task completed');
    } catch (err) {
      logger.error('Failed to run maintenance task', err);
    }
  }, maintenanceInterval);
}).catch(async (err)=>{
  logger.error('Failed to connect to the database', err);
  await closeDatabaseConnection();
});
const gracefulShutdown = async ()=>{
  logger.info('Received shutdown signal, closing server...');
  if (server) {
    server.close(async (err)=>{
      if (err) {
        logger.error('Error closing server:', err);
      }
      logger.info('Server closed');
      await closeDatabaseConnection();
    });
  } else {
    await closeDatabaseConnection();
  }
};
const handleSignal = async ()=>{
  logger.debug("handling signal, calling gracefulShutdown!");
  await gracefulShutdown();
};
