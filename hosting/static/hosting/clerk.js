async function initializeClerk() {
  const signIn = document.querySelector("#clerk-sign-in");
  const userButton = document.querySelector("#clerk-user");

  try {
    await window.Clerk.load({ ui: { ClerkUI: window.__internal_ClerkUICtor } });
    if (signIn) {
      const after = new URL(signIn.dataset.after, location.origin).href;
      if (window.Clerk.user) {
        location.replace(after);
        return;
      }
      window.Clerk.mountSignIn(signIn, {
        routing: "hash",
        fallbackRedirectUrl: after,
        signUpFallbackRedirectUrl: after,
      });
    }
    if (userButton && window.Clerk.user) {
      window.Clerk.mountUserButton(userButton);
    }
  } catch (error) {
    console.error("WNBase Clerk initialization failed", error);
    if (signIn) {
      signIn.textContent = "Clerk sign-in is unavailable. Reload to try again.";
    }
  }
}

window.addEventListener("load", initializeClerk, { once: true });
