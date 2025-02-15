import { assert } from "./logger.ts";
// @deno-types="npm:@types/msgpack-lite"
import msgpack from 'msgpack-lite';
import { insertLocationEvent } from "./mongodb.ts";
function unbias(i, f, a) {
  if (0 <= i && i <= a - 1) {
    i = i + 1;
    return i - f;
  } else if (a <= i && i <= 2 * a) {
    i = i - a;
    let x = i - f;
    if (x != 0) {
      x = -x;
    }
    return x;
  } else {
    assert(false) // i not in [0, 2a]
    ;
  }
}
export function validateLocationEvent(req) {
  const buffer = req.body;
  // fast checks
  assert(buffer[0] == 0x84) // must be object with 4 keys (v, t, d, m)
  ;
  assert(buffer[1] == 0xA1 && buffer[2] == 0x76) // first key is 'v'
  ;
  assert(buffer[3] == 0xA8 && buffer[4] == 0x65) // vids are 8 character strings starting with e
  ;
  // slower msgpack decode and other validation
  const msg = msgpack.decode(buffer); // throws on bad decode
  let vid = msg.v // already checked above
  ;
  assert(vid) // fail fast
  ;
  let timestamp = msg.t // too old/new checked on event insert
  ;
  assert(timestamp) // fail fast
  ;
  // translate & check coordinates from msg.d (bias-packed degrees) and msg.m (bit-packed milliseconds)
  // convert to D.DDDDDD accuracy at least 0.000017 or approx 2 meters
  let lat_ms = msg.m >> 16 & 0xFFFF;
  let lon_ms = msg.m & 0xFFFF;
  let lat_s = lat_ms / 1000;
  let lon_s = lon_ms / 1000;
  let lat_df = lat_s / 60;
  let lon_df = lon_s / 60;
  let lat_di = Math.trunc(msg.d / 361);
  let lon_di = msg.d % 361;
  let lat = unbias(lat_di, lat_df, 90);
  let lon = unbias(lon_di, lon_df, 180);
  assert(-90 <= lat && lat <= 90) // latitude range check.  range is [-90, 90]
  ;
  assert(-180 <= lon && lon <= 180) // longitude range check. range is [-180, 180]
  ;
  assert(!(lat == 0 && lon == 0)) // avoid bogus coordinates (null island)
  ;
  const event = {
    vid: vid,
    timestamp: timestamp,
    point: {
      type: "Point",
      coordinates: [
        lon,
        lat
      ] // GeoJSON Point expects longitude first
    }
  };
  return event;
}
export function registerRoutes(app) {
  app.post("/event/insert", async (req, res)=>{
    try {
      const event = validateLocationEvent(req);
      await insertLocationEvent(event);
      res.status(200).send("Event inserted successfully");
    } catch (error) {
      res.status(500).send("Error inserting event: " + error);
    }
  });
  app.post("/event/test", async (req, res)=>{
    try {
      const event = {
        vid: "e-00-000",
        timestamp: new Date().getTime(),
        point: {
          type: "Point",
          coordinates: [
            0,
            0
          ] // visiting null island
        }
      };
      await insertLocationEvent(event);
      res.status(200).send("Event inserted successfully");
    } catch (error) {
      res.status(500).send("Error inserting event: " + error);
    }
  });
}
