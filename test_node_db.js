const { Client } = require('pg');

const connStr = 'postgresql://postgres.gfcogtusrrfeaxckihxx:YFcR6EG0EC1hhyWr@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres?sslmode=require';

const client = new Client({
  connectionString: connStr,
  ssl: { rejectUnauthorized: false }
});

async function test() {
  try {
    console.log('Connecting via Node pg...');
    await client.connect();
    const res = await client.query('SELECT NOW()');
    console.log('Node JS Connection SUCCESS!', res.rows[0]);
  } catch (err) {
    console.error('Node JS Connection ERROR:', err.message);
  } finally {
    await client.end();
  }
}

test();
