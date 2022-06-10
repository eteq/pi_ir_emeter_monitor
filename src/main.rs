use std::error::Error;
//use std::thread::sleep;
use std::time::{SystemTime, Duration, UNIX_EPOCH};

use rusqlite::{Connection, Result};

use rppal::gpio;

const PULSE_PIN: u8 = 24; //BCM pin #


fn setup_db(path: &str) -> Result<Connection>{
    let conn = Connection::open(path)?;

    conn.execute(
        "CREATE TABLE IF NOT EXISTS wh_pulses (
            id              INTEGER PRIMARY KEY,
            tstampunixns            INTEGER NOT NULL
        )",
        [], // empty list of parameters.
    )?;

    Ok(conn)
}


fn main() -> Result<(), Box<dyn Error>> {
    let log_path = "power_mon.sqlite3";

    let db = setup_db(log_path)?;
    println!("Completed setup of sqlite db file {}", log_path);

    let g = gpio::Gpio::new()?;

    let mut pin = g.get(PULSE_PIN)?.into_input();
    pin.set_interrupt(gpio::Trigger::Both)?;

    let mut t1 = SystemTime::now();
    let mut t_last_pulse = t1;

    loop {
        let level = match pin.poll_interrupt(true, Some(Duration::new(120, 0)))? {
            Some(l) => l,
            None => {break;}
        };
        let t2 = SystemTime::now();

        let since_last_edge =  t2.duration_since(t1)?;
        let since_last_edge_ms = since_last_edge.as_millis();

        if 23 < since_last_edge_ms && since_last_edge_ms < 26 {
            // a watt-hour pulse should be ~25 ms
            let since_last_pulse_ms =  t2.duration_since(t_last_pulse)?.as_millis();
            let since_last_pulse_watts = 3600000. / since_last_pulse_ms as f32;
            if level == gpio::Level::High {
                // rising
                println!("Warning: a ~25 ms pulse of {} ns was rising, but logging anyway. Time since last pulse: {} ms = {} W", 
                         since_last_edge.as_nanos(), since_last_pulse_ms, since_last_pulse_watts);
            }  else {
                println!("falling edge pulse of {} ns, logging. Time since last pulse: {} ms = {} W", 
                         since_last_edge.as_nanos(), since_last_pulse_ms, since_last_pulse_watts);
            }

            let unix_time_nanos = t2.duration_since(UNIX_EPOCH)?.as_nanos() as u64;
            db.execute("INSERT INTO wh_pulses (tstampunixns) VALUES (?1)", 
                       [&unix_time_nanos])?;

            t_last_pulse = t2;
        }
        t1 = t2;
    }

    println!("Timed out waiting for a pulse");
    Ok(())
}
