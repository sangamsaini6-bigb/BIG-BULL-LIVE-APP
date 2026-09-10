package com.bigbull.pnl.mobile;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.ViewGroup;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.TextView;

public class MainActivity extends Activity {
  private WebView webView;
  @Override public void onCreate(Bundle b) { super.onCreate(b); splash(); new Handler(Looper.getMainLooper()).postDelayed(this::openApp,650); }
  private void splash() {
    FrameLayout root=new FrameLayout(this); root.setBackgroundColor(Color.rgb(8,9,11));
    ImageView logo=new ImageView(this); logo.setImageResource(R.drawable.big_bull_logo); logo.setScaleType(ImageView.ScaleType.CENTER_INSIDE);
    int s=(int)(260*getResources().getDisplayMetrics().density); FrameLayout.LayoutParams lp=new FrameLayout.LayoutParams(s,s); lp.gravity=Gravity.CENTER; root.addView(logo,lp); setContentView(root);
  }
  private void openApp() {
    try {
      webView=new WebView(this); webView.setLayoutParams(new ViewGroup.LayoutParams(-1,-1)); webView.setBackgroundColor(Color.rgb(8,9,11));
      WebSettings s=webView.getSettings(); s.setJavaScriptEnabled(true); s.setDomStorageEnabled(true); s.setAllowFileAccess(true); s.setAllowContentAccess(true); s.setDatabaseEnabled(true); s.setLoadWithOverviewMode(true); s.setUseWideViewPort(true);
      webView.setWebViewClient(new WebViewClient()); webView.setWebChromeClient(new WebChromeClient()); setContentView(webView); webView.loadUrl("file:///android_asset/index.html");
    } catch(Throwable t) {
      TextView v=new TextView(this); v.setText("BIG BULL could not start.\n\n"+t.getMessage()); v.setTextColor(Color.WHITE); v.setBackgroundColor(Color.rgb(8,9,11)); v.setPadding(32,64,32,32); setContentView(v);
    }
  }
  @Override public void onBackPressed(){ if(webView!=null&&webView.canGoBack()) webView.goBack(); else super.onBackPressed(); }
}
