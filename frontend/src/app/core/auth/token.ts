export function getTokenExpiryEpochSeconds(token: string): number | null {
    try {
        const payload = token.split(".")[1];
        if (!payload) {
            return null;
        }

        const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
        const decoded = JSON.parse(atob(normalized)) as { exp?: unknown };
        return typeof decoded.exp === "number" ? decoded.exp : null;
    } catch {
        return null;
    }
}

export function isTokenExpired(token: string, skewSeconds = 30): boolean {
    const exp = getTokenExpiryEpochSeconds(token);
    if (exp === null) {
        return true;
    }

    return Date.now() >= (exp - skewSeconds) * 1000;
}
