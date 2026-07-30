const BUILD_VERSION = "github-on-demand-20260731";
const GITHUB_OWNER = "forest16811";
const GITHUB_REPO = "binance-p2p-vnd-network-test";
const GITHUB_WORKFLOW = "binance-test.yml";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/health") {
      return Response.json({
        ok: true,
        version: BUILD_VERSION,
        githubConfigured: Boolean(env.GH_PAT),
        callbackConfigured: Boolean(env.CALLBACK_SECRET),
      });
    }

    if (url.pathname === "/setup") {
      return setupTelegramWebhook(url, env);
    }

    if (request.method === "POST" && url.pathname === "/github-result") {
      return receiveGitHubResult(request, env);
    }

    if (request.method === "POST" && url.pathname === "/telegram") {
      return receiveTelegramUpdate(request, env);
    }

    return new Response("Binance VND Telegram Bot is running.", {
      status: 200,
    });
  },
};

async function setupTelegramWebhook(url, env) {
  if (!env.BOT_TOKEN) {
    return Response.json(
      { ok: false, error: "BOT_TOKEN is missing" },
      { status: 500 },
    );
  }

  const webhookUrl = `${url.origin}/telegram`;
  const telegramResponse = await fetch(
    `https://api.telegram.org/bot${env.BOT_TOKEN}/setWebhook`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: webhookUrl,
        drop_pending_updates: true,
        ...(env.WEBHOOK_SECRET
          ? { secret_token: env.WEBHOOK_SECRET }
          : {}),
      }),
    },
  );
  const result = await telegramResponse.json();
  return Response.json(result, { status: telegramResponse.status });
}

async function receiveTelegramUpdate(request, env) {
  if (
    env.WEBHOOK_SECRET &&
    request.headers.get("X-Telegram-Bot-Api-Secret-Token") !==
      env.WEBHOOK_SECRET
  ) {
    return new Response("Unauthorized", { status: 401 });
  }

  let update;
  try {
    update = await request.json();
  } catch {
    return new Response("Bad request", { status: 400 });
  }

  const message = update.message;
  const command = message?.text?.trim().toLowerCase();
  if (!message?.chat?.id || command !== "z0") {
    return new Response("OK");
  }

  const chatId = String(message.chat.id);
  const requestId = `${Date.now()}-${crypto.randomUUID()}`;

  try {
    await dispatchGitHubWorkflow(env.GH_PAT, chatId, requestId);
    await sendMessage(
      env.BOT_TOKEN,
      chatId,
      "正在查询 Binance 越南盾购买 USDT 的实时前10名，请稍候（通常需要10～60秒）。",
    );
  } catch (error) {
    const reason = error?.message ?? String(error);
    console.error(`GitHub dispatch failed: ${reason}`);
    await sendMessage(
      env.BOT_TOKEN,
      chatId,
      `查询任务启动失败，请稍后再试。\n错误信息：${reason}`,
    );
  }

  return new Response("OK");
}

async function receiveGitHubResult(request, env) {
  if (
    !env.CALLBACK_SECRET ||
    request.headers.get("X-Callback-Secret") !== env.CALLBACK_SECRET
  ) {
    return new Response("Unauthorized", { status: 401 });
  }

  let result;
  try {
    result = await request.json();
  } catch {
    return new Response("Bad request", { status: 400 });
  }

  const chatId = String(result?.chat_id ?? "");
  const text = String(result?.text ?? "");
  if (!chatId || !text) {
    return new Response("Missing chat_id or text", { status: 400 });
  }

  await sendMessage(env.BOT_TOKEN, chatId, text);
  return Response.json({ ok: true, requestId: result?.request_id ?? null });
}

async function dispatchGitHubWorkflow(token, chatId, requestId) {
  if (!token) {
    throw new Error("GH_PAT is missing");
  }

  const response = await fetch(
    `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/workflows/${GITHUB_WORKFLOW}/dispatches`,
    {
      method: "POST",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        "User-Agent": "binance-vnd-telegram-worker",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      body: JSON.stringify({
        ref: "main",
        inputs: {
          chat_id: chatId,
          request_id: requestId,
        },
      }),
    },
  );

  if (!response.ok) {
    const detail = (await response.text()).slice(0, 300);
    throw new Error(`GitHub HTTP ${response.status}: ${detail}`);
  }
}

async function sendMessage(token, chatId, text) {
  if (!token) {
    throw new Error("BOT_TOKEN is missing");
  }

  const response = await fetch(
    `https://api.telegram.org/bot${token}/sendMessage`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: chatId,
        text,
        disable_web_page_preview: true,
      }),
    },
  );

  if (!response.ok) {
    const detail = (await response.text()).slice(0, 200);
    throw new Error(`Telegram HTTP ${response.status}: ${detail}`);
  }
}
