import { MongoClient, ObjectId, MongoInvalidArgumentError } from "mongodb";
import { logger } from './logger.ts';
const CLOCK_THRESH = +(60000);
let client;
let db;
let dbName;
let locationEvents;
let locationHistory;
export async function connectToDatabase(uri, dbName_) {
  client = new MongoClient(uri);
  try {
    await client.connect();
    logger.info('Connected to MongoDB');
  } catch (err) {
    logger.error('Failed to connect to MongoDB', err);
    throw err;
  }
  db = client.db(dbName_);
  dbName = dbName_;
  await createCollections();
}
async function createCollections() {
  // existance check not needed for mongodb 7.0
  if (!((await db.listCollections({ name: "location_events" }).toArray()).length == 0)) { // start fresh
    locationEvents = db.collection("location_events");
    await locationEvents.drop();
  }
  if (!((await db.listCollections({ name: "location_history" }).toArray()).length == 0)) { // start fresh
    locationHistory = db.collection("location_history");
    await locationHistory.drop();
  }
  await db.createCollection("location_events", {
    capped: true,
    max: 10000,
    size: 10000 * 128
  });
  locationEvents = db.collection("location_events");
  await locationEvents.createIndex({
    vid: 1,
    timestamp: 1
  }, {
    unique: true
  }) // avoid duplicates and make aggregate faster
  ;
  locationHistory = db.collection("location_history");

  var data1 = {
    _id: new ObjectId(),
    vid: "e-00-000",
    count: 3,
    starttime: 1733510923697,
    endtime: 1733510925697,
    timestamps: [
      1733510923697, 1733510924697, 1733510925697
    ],
    lineString: {
      type: "LineString",
      coordinates: [
        [10, 100], [11, 101], [12, 102]
      ]
    }
  }
  await locationHistory.insertOne(data1);

  var data2 = {
    _id: new ObjectId(),
    vid: "e-00-001",
    count: 1,
    starttime: 1733510923697,
    endtime: 1733510923697,
    timestamps: [
      1733510923697
    ],
    lineString: {
      type: "LineString",
      coordinates: [
        [20, 120]
      ]
    }
  }
  await locationHistory.insertOne(data2);

  var data3 = {
    _id: new ObjectId(),
    vid: "e-00-002",
    count: 1,
    starttime: 1733510923697,
    endtime: 1733510923697,
    timestamps: [
      1733510923697
    ],
    lineString: {
      type: "LineString",
      coordinates: [
        [30, 130]
      ]
    }
  }
  await locationHistory.insertOne(data3);

  var data4 = {
    _id: new ObjectId(),
    vid: "e-00-003",
    count: 1,
    starttime: 1733510923697,
    endtime: 1733510923697,
    timestamps: [
      1733510923697
    ],
    lineString: {
      type: "LineString",
      coordinates: [
        [40, 140]
      ]
    }
  }
  await locationHistory.insertOne(data4);
}
export async function closeDatabaseConnection() {
  if (client) {
    await client.close();
    logger.info('Disconnected from MongoDB');
  }
}
// only for testing
export async function clearDatabase() {
  await locationEvents.drop();
  await locationHistory.drop();
  logger.debug("Dropped collections in db '" + dbName + "'");
  // now recreate collections (since drop destroys indexes etc)
  await createCollections();
}
// only for testing
export async function getLocationEvents(filter) {
  return await locationEvents.find(filter).toArray();
}
// only for testing
export async function getLocationHistory(filter) {
  return await locationHistory.find(filter).toArray();
}
export async function insertLocationEvent(event, force = false) {
  if (!force) {
    const currentTime = new Date();
    if (Math.abs(currentTime.getTime() - event.timestamp) > CLOCK_THRESH) {
      throw new Error("Event timestamp is not within range of the current time");
    }
  }
  let doc = {
    _id: new ObjectId(),
    ...event
  }; // force new id to avoid duplicate key error on fast insertions
  await locationEvents.insertOne(doc);
}
function paginate(h, max_count, prev_count) {
  // split the single "h" LocationHistory into an array of LocationHistory values
  // each should have a maximum "count" value (ie. number of timestamps and number of coordinates) of max_count paramater
  // but the first LocationHistory should have (max_count-prev_count) as it's maximum "count"
  if (h.count <= max_count - prev_count) return [
    h
  ]; // optimize typical case
  // here at least 1 split is needed
  const paginatedHistories = [];
  let used = 0;
  let available = max_count - prev_count;
  while(used < h.count){
    let currentHistory = {
      vid: h.vid,
      count: available,
      starttime: h.timestamps[used],
      endtime: h.timestamps[used + available - 1],
      timestamps: h.timestamps.slice(used, used + available),
      lineString: {
        type: "LineString",
        coordinates: h.lineString.coordinates.slice(used, used + available)
      }
    };
    paginatedHistories.push(currentHistory);
    used += available;
    available = Math.min(max_count, h.count - used);
  }
  return paginatedHistories;
}
export async function aggregateLocationEvents() {
  const pipeline = [
    {
      $sort: {
        vid: 1,
        timestamp: 1
      } // so groups have entries ordered by time (optimized with index)
    },
    {
      $group: {
        _id: "$vid",
        last_id: {
          $max: "$_id"
        },
        starttime: {
          $min: "$timestamp"
        },
        endtime: {
          $max: "$timestamp"
        },
        timestamps: {
          $push: "$timestamp"
        },
        coords: {
          $push: "$point.coordinates"
        }
      }
    },
    {
      $project: {
        location_history: {
          _id: "$last_id",
          vid: "$_id",
          count: {
            $size: "$timestamps"
          },
          starttime: "$starttime",
          endtime: "$endtime",
          timestamps: "$timestamps",
          lineString: {
            type: "LineString",
            coordinates: "$coords"
          }
        }
      }
    }
  ];
  const aggregatedResults = await locationEvents.aggregate(pipeline).toArray();
  if (aggregatedResults.length == 0) return;
  const MAX_COUNT = 100; // max events in a single LocationHistory to avoid Mongo errors
  var bulk = locationHistory.initializeUnorderedBulkOp();
  var last_id = new ObjectId(0);
  for (var result of aggregatedResults){
    let h = result.location_history;
    if (h._id > last_id) last_id = h._id; // keep the last id across all groups
    let last_history_selector = {
      vid: h.vid
    };
    logger.info("last_history_selector:" , JSON.stringify(last_history_selector));
    let last_history = (await locationHistory.find(last_history_selector).sort({
      endtime: -1
    }).limit(1).toArray()).shift();
    logger.info("last_history:" , JSON.stringify(last_history));
    if (last_history == null) {
      let histories = paginate(h, MAX_COUNT, 0);
      for (var newh of histories){
        logger.info("[last_history is null, therefore INSERTING] newh:" , JSON.stringify(newh));
        await bulk.insert(newh);
      }
    } else {
      last_history_selector.endtime = last_history.endtime; // now we can select the correct history to extend
      logger.info("h.starttime:" , JSON.stringify(h.starttime));
      logger.info("last_history.endtime:" , JSON.stringify(last_history.endtime));
      if (h.starttime >= last_history.endtime) {
        let histories = paginate(h, MAX_COUNT, last_history.count);
        let extra = histories.shift();
        // update last history up to the MAX_COUNT locations
        last_history.count += extra.count;
        last_history.endtime = extra.endtime;
        last_history.timestamps.push(...extra.timestamps);
        last_history.lineString.coordinates.push(...extra.lineString.coordinates);
        logger.info("[DATA EXISTS, UPDATING RECORDS...]");
        logger.info("last_history_selector:" , JSON.stringify(last_history_selector));
        await bulk.find(last_history_selector).update({
          $set: {
            count: last_history.count,
            endtime: last_history.endtime,
            timestamps: last_history.timestamps,
            lineString: last_history.lineString
          }
        });
        // add complete additional history entries over MAX_COUNT
        for (var newh of histories){
          await bulk.insert(h);
        }
      } else {
      // just drop it since we already have a newer location, maybe implement later
      //throw new Error("todo");
      }
    }
  }
  try {
    await bulk.execute();
  } catch (e) {
    if (e instanceof MongoInvalidArgumentError) {
      // MongoInvalidArgumentError: Invalid BulkOperation, Batch cannot be empty
      logger.debug("handled exception in aggregateLocationEvents", e);
    } else {
      logger.error("unhandled exception in aggregateLocationEvents", e);
    }
  }
  // clear the locationEvents collection after aggregation up to and including the last_id
  await locationEvents.deleteMany({
    _id: {
      $lte: last_id
    }
  });
}
