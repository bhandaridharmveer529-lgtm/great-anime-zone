export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    try {
      const animeName = url.searchParams.get('anime');
      const epNum = url.searchParams.get('ep') || '1';
      const type = url.searchParams.get('type') || 'dub';

      if (!animeName) {
        return new Response(JSON.stringify({ 
          error: 'Anime name required',
          usage: '?anime=Naruto&ep=1&type=dub'
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      const searchUrl = `https://hianime-api-iy4s.onrender.com/api/search?keyword=${encodeURIComponent(animeName)}`;
      const searchRes = await fetch(searchUrl);
      const searchData = await searchRes.json();

      if (!searchData.results || searchData.results.length === 0) {
        return new Response(JSON.stringify({ error: 'Anime not found' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      const animeId = searchData.results[0].id;

      const epUrl = `https://hianime-api-iy4s.onrender.com/api/episodes/${animeId}`;
      const epRes = await fetch(epUrl);
      const epData = await epRes.json();

      if (!epData.episodes || !epData.episodes[epNum - 1]) {
        return new Response(JSON.stringify({ error: 'Episode not found' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      const epId = epData.episodes[epNum - 1].id;

      const servers = ['HD-2', 'HD-1', 'StreamSB', 'StreamTape'];
      let streamData = null;

      for (const server of servers) {
        try {
          const streamUrl = `https://hianime-api-iy4s.onrender.com/api/stream?id=${epId}&type=${type}&server=${server}`;
          const streamRes = await fetch(streamUrl);
          const data = await streamRes.json();
          
          if (data.sources && data.sources.length > 0) {
            streamData = data;
            streamData.server = server;
            streamData.type = type;
            break;
          }
        } catch (e) {
          continue;
        }
      }

      if (!streamData && type === 'dub') {
        for (const server of servers) {
          try {
            const streamUrl = `https://hianime-api-iy4s.onrender.com/api/stream?id=${epId}&type=sub&server=${server}`;
            const streamRes = await fetch(streamUrl);
            const data = await streamRes.json();
            
            if (data.sources && data.sources.length > 0) {
              streamData = data;
              streamData.server = server;
              streamData.type = 'sub';
              break;
            }
          } catch (e) {
            continue;
          }
        }
      }

      if (!streamData) {
        return new Response(JSON.stringify({ error: 'No stream found' }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      return new Response(JSON.stringify(streamData), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });

    } catch (e) {
      return new Response(JSON.stringify({ error: e.message }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }
  }
};
