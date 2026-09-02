export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-50 px-6 text-center dark:bg-black">
      <p className="mb-3 text-sm font-medium uppercase tracking-widest text-zinc-500">
        TeleCommerce
      </p>
      <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50 sm:text-5xl">
        Shop from Web. Shop from Telegram.
      </h1>
      <p className="mt-6 max-w-xl text-lg text-zinc-600 dark:text-zinc-400">
        A multi-channel commerce platform with a shared backend, web
        storefront, and Telegram commerce interface. Under active
        development &mdash; Stage 1: Foundation.
      </p>
    </div>
  );
}
