package com.signalrescue.mesh
import com.facebook.react.ReactPackage
import com.facebook.react.bridge.*
import com.facebook.react.uimanager.ViewManager
class MeshNativePackage:ReactPackage{override fun createNativeModules(c:ReactApplicationContext)=listOf(MeshNativeModule(c));override fun createViewManagers(c:ReactApplicationContext)=emptyList<ViewManager<*,*>>()}
