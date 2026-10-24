package api

import (
 "net/http"
 "net/http/httptest"
 "testing"
 "video-streaming-api/internal/config"
 "github.com/gin-gonic/gin"
 "github.com/sirupsen/logrus"
)

func TestSpoofedForwardingHeadersNeverExemptAPIKey(t *testing.T) {
 gin.SetMode(gin.TestMode)
 cfg := &config.SecurityConfig{APIKeyEnabled:true, APIKeys:[]string{"secret"}, APIKeyHeader:"X-API-Key", APIKeyExemptIPs:[]string{"127.0.0.1"}}
 router:=gin.New()
 if err:=router.SetTrustedProxies(nil);err!=nil { t.Fatal(err) }
 router.Use(APIKeyAuthMiddleware(cfg,logrus.New()))
 router.GET("/secure",func(c *gin.Context){c.Status(http.StatusNoContent)})
 req:=httptest.NewRequest(http.MethodGet,"/secure",nil)
 req.RemoteAddr="203.0.113.7:12345"
 req.Header.Set("X-Forwarded-For","127.0.0.1")
 req.Header.Set("X-Real-IP","127.0.0.1")
 req.Header.Set("CF-Connecting-IP","127.0.0.1")
 w:=httptest.NewRecorder()
 router.ServeHTTP(w,req)
 if w.Code!=http.StatusUnauthorized {t.Fatalf("bypassed auth via headers: %d",w.Code)}
 req.Header.Set("X-API-Key","secret")
 w=httptest.NewRecorder()
 router.ServeHTTP(w,req)
 if w.Code!=http.StatusNoContent {t.Fatalf("valid key rejected: %d",w.Code)}
}

func TestCORSPreflightBeforeAPIKeyAuthentication(t *testing.T) {
 gin.SetMode(gin.TestMode)
 cfg:=&config.SecurityConfig{APIKeyEnabled:true,APIKeys:[]string{"secret"},APIKeyHeader:"X-API-Key",CORSAllowedOrigins:[]string{"https://example.org"},CORSAllowedMethods:[]string{"GET","OPTIONS"},CORSAllowedHeaders:[]string{"X-API-Key"}}
 router:=gin.New()
 router.Use(ConfigurableCORSMiddleware(cfg),APIKeyAuthMiddleware(cfg,logrus.New()))
 router.GET("/secure",func(c *gin.Context){c.Status(http.StatusNoContent)})
 for _,tc:=range []struct{origin string; want int}{{"https://example.org",204},{"https://evil.org",403}} {
  req:=httptest.NewRequest(http.MethodOptions,"/secure",nil)
  req.Header.Set("Origin",tc.origin)
  req.Header.Set("Access-Control-Request-Method","GET")
  w:=httptest.NewRecorder()
  router.ServeHTTP(w,req)
  if w.Code!=tc.want {t.Errorf("%s returned %d, want %d",tc.origin,w.Code,tc.want)}
 }
}

func TestGetClientIPUsesPeer(t *testing.T) {
 if got:=GetClientIP(map[string][]string{"CF-Connecting-IP":{"127.0.0.1"}},"203.0.113.7:1234");got!="203.0.113.7" {t.Fatalf("got spoofed IP %q",got)}
}
