import service from "./index.js";

export function fetchSourceUrls(urls) {
  return service({
    url: "/api/sources/fetch",
    method: "post",
    data: { urls },
  });
}
