async function initializeClerk() {
  const signIn = document.querySelector("#clerk-sign-in");
  const userButton = document.querySelector("#clerk-user");

  try {
    await window.Clerk.load();
    if (signIn) {
      const after = new URL(signIn.dataset.after, location.origin).href;
      if (window.Clerk.user) {
        location.replace(after);
        return;
      }
      window.Clerk.mountSignIn(signIn, {
        fallbackRedirectUrl: after,
        signUpFallbackRedirectUrl: after,
      });
    }
    if (userButton && window.Clerk.user) {
      window.Clerk.mountUserButton(userButton);
    }
  } catch {
    if (signIn) {
      signIn.textContent = "Clerk sign-in is unavailable. Reload to try again.";
    }
  }
}

initializeClerk();
