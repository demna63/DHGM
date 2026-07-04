package com.atakmap.app;

import android.annotation.TargetApi;
import android.content.Context;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.Manifest;

import com.atakmap.coremap.log.Log;

import android.app.AlertDialog;
import android.content.DialogInterface;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.Settings;
import android.view.LayoutInflater;
import android.view.View;

import androidx.annotation.NonNull;

/**
 * DHGM override (custom/overlay): upstream-ის Permissions.java გაშვებისას ითხოვს
 * ყველა ნებართვას (კამერა, მიკროფონი, SMS, ტელეფონი, background GPS) და უარზე
 * აპი იხურება. DHGM-ში აუცილებელია მხოლოდ ფაილებზე წვდომა (რუკები/იმპორტი) —
 * დანარჩენი ნებაყოფლობითია და საჭიროებისას სისტემის პარამეტრებიდან ჩაირთვება.
 */
public class Permissions {

    private final static String TAG = "Permissions";

    final static int REQUEST_ID = 90402;

    final static int LOCATION_REQUEST_ID = 90403;

    // DHGM: მხოლოდ ის runtime ნებართვები, რომელთა გარეშეც ბირთვი ვერ იმუშავებს
    final static String[] PermissionsList = new String[] {
            Manifest.permission.WRITE_EXTERNAL_STORAGE,
            Manifest.permission.READ_EXTERNAL_STORAGE,
    };

    final static String[] locationPermissionsList = new String[] {
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_LOCATION_EXTRA_COMMANDS,
    };

    static boolean checkPermissions(final Activity a) {

        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) {
            return true;
        }

        // Android 11+ (R): READ/WRITE_EXTERNAL_STORAGE აღარ გაიცემა (scoped storage) —
        // მათი მოთხოვნა მარყუჟს ქმნის. DHGM აქ საერთოდ არ ბლოკავს გაშვებას; რუკის
        // ფაილებზე სრული წვდომა (All files access) ნებაყოფლობითია და მოგვიანებით,
        // არა-მბლოკავად ეთხოვება მომხმარებელს (იხ. maybePromptAllFilesAccess).
        // Android 11+: არ ვაჩვენებთ All-files-access დიალოგს გაშვებისას —
        // upstream encryption/EULA დიალოგებთან ერთად ეკრანს ფარავდა და splash-ზე ჭედავდა.
        // სრული წვდომა: პარამეტრები → აპის სისტემის პარამეტრები (იხ. smoke-test.md).
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            Log.d(TAG, "DHGM: startup not gated on Android 11+ "
                    + "(storage/camera/mic/location all optional)");
            return true;
        }

        // Android 6..10 (M..Q): legacy storage ნებართვა ჯერ კიდევ გაიცემა
        int result = 0;
        for (String permission : PermissionsList) {
            result += a.checkSelfPermission(permission);
        }
        if (result != PackageManager.PERMISSION_GRANTED) {
            Log.d(TAG, "DHGM: requesting legacy storage permissions (pre-R)");
            a.requestPermissions(PermissionsList, REQUEST_ID);
            return false;
        }
        return true;
    }

    @TargetApi(30)
    private static void showFileSystemWarning(final Activity a) {
        LayoutInflater li = LayoutInflater.from(a);
        View v = li.inflate(R.layout.storage_permission_guidance, null);

        final AlertDialog.Builder builder = new AlertDialog.Builder(a);
        builder.setTitle(R.string.file_system_access_changes);
        builder.setView(v);
        builder.setIcon(R.drawable.ic_database);
        builder.setCancelable(false);

        builder.setPositiveButton(R.string.i_understand,
                new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface dialog, int which) {
                        final Uri uri = Uri
                                .parse("package:" + BuildConfig.APPLICATION_ID);
                        final Intent intent = new Intent(
                                Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION,
                                uri);
                        a.startActivityForResult(intent, REQUEST_ID);
                    }
                });

        builder.setNegativeButton(R.string.cancel,
                new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface dialog, int which) {
                        a.finish();
                    }
                });

        builder.show();
    }

    static void displayNeverAskAgainDialog(final Activity a) {

        View view = LayoutInflater.from(a).inflate(
                R.layout.general_permission_guidance,
                null);

        final AlertDialog.Builder builder = new AlertDialog.Builder(a);
        builder.setTitle(R.string.required_missing_permissions);
        builder.setView(view);
        builder.setCancelable(false);
        builder.setPositiveButton(R.string.i_understand,
                new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface dialog, int which) {
                        dialog.dismiss();
                        Intent intent = new Intent();
                        intent.setAction(
                                android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
                        Uri uri = Uri.fromParts("package", a.getPackageName(),
                                null);
                        intent.setData(uri);
                        a.startActivityForResult(intent, REQUEST_ID);
                    }
                }).setNegativeButton(R.string.cancel,
                        new DialogInterface.OnClickListener() {
                            @Override
                            public void onClick(DialogInterface dialog,
                                    int which) {
                                a.finish();
                            }
                        });
        builder.show();
    }

    /**
     * Check to make sure that the required permission has been granted.
     * @param context the context
     * @param permission the permission
     * @return true if the permission has been granted.
     */
    public static boolean checkPermission(final Context context,
            final String permission) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) {
            return true;
        }

        final int result = context.checkSelfPermission(permission);
        if (result == PackageManager.PERMISSION_GRANTED) {
            return true;
        } else {
            Log.e(TAG, "permission denied: " + permission, new Exception());
            return false;
        }

    }

    /**
     * Handles the mechanics of the permission request.
     * @param requestCode must be Permissions.REQUEST_ID
     * @param permissions the list of permissions requested
     * @param grantResults the results for each of the permissions
     * @return true if the permissions have all been granted
     */
    static boolean onRequestPermissionsResult(int requestCode,
            @NonNull String[] permissions, @NonNull int[] grantResults) {

        Log.d(TAG, "onRequestPermissionsResult called: " + requestCode);
        switch (requestCode) {
            case Permissions.LOCATION_REQUEST_ID:
            case Permissions.REQUEST_ID:
                if (grantResults.length > 0) {
                    boolean b = true;
                    for (int i = 0; i < grantResults.length; ++i) {
                        b = b && (grantResults[i] == PackageManager.PERMISSION_GRANTED);
                        if (grantResults[i] != PackageManager.PERMISSION_GRANTED)
                            Log.d(TAG, "onRequestPermissionResult not granted: "
                                    + permissions[i]);
                    }

                    return b;

                }
        }
        return false;

    }

}
