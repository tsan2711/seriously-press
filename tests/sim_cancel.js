const RC = require(process.argv[2]), ac = { aborted: false };
const fx = async u => { ac.aborted = true; return { ok: true, text: async () => '<rss></rss>', json: async () => ({ hits: [] }) }; };
RC.run({ fetch: fx, signal: ac, sources: [{ id: 'a', name: 'A', url: 'https://a.test/f', desk: 'x' }, { id: 'b', name: 'B', url: 'https://b.test/f', desk: 'x' }], hn: [], topics: {}, known: [] })
  .then(() => console.log(JSON.stringify({ run_cancel: false })), e => console.log(JSON.stringify({ run_cancel: e.message === 'Đã huỷ' })));
