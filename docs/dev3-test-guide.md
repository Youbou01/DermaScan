. Create test accounts and open a demo product

1. In the app, open **Account** and choose **Create an account**.
2. Create **Account A** with a disposable test email and a password of at least 8 characters.
3. Sign out, create a second, separate test account (**Account B**) with a different disposable email, and leave its skin profile blank. Then sign out and sign back in as Account A. Do not use a real person's account.
4. Open **Skin profile** for Account A, select **Dry**, then choose **Save profile**. This is used to check personalized guidance.
5. To open a demo product, use the app's **Scan** screen, enter one of the barcodes above in the Barcode field, and choose **Find product**. You can also open a product card from Home. Return to Home using the app navigation.

Expected result: the product detail screen displays the selected demo product. Opening a product while signed in records it in Account A's recently viewed list.


. Try the personal library

.1 Saved products

1. Sign out. From Home, open **Saved products**. Confirm the screen asks you to sign in.
2. Sign in as Account A and open a demo product.
3. On the product screen, choose **Save product**. Reopen the screen or wait for the saved state to refresh; the control should now show that it is saved.
4. From Home or Account, open **Saved products**. Confirm the product appears.
5. The product screen uses a toggle. Do not tap it again unless you intend to remove the product. To verify repeat-save idempotency, use the authenticated API test or the backend integration test listed below.
6. Remove it from the library using the row's remove action (or toggle the saved control on its product screen). Confirm it disappears. Save it again if you need it for a later step.

Expected result: saving and removing update the list, and signed-out users see the sign-in gate.

.2 Recently viewed

1. While signed in as Account A, open two or more different demo products using Scan or Home.
2. From Home or Account, open **Recently viewed**.
3. Confirm the most recently opened product appears first.
4. Reopen the earlier product, then revisit **Recently viewed**. Confirm it moves to the top and does not appear twice.
5. Sign out and sign in as Account B. Open **Recently viewed**. Confirm Account A's history is not shown. The same privacy check can be done for **Saved products**.
6. Sign back in as Account A and confirm its library remains.

The demo seed contains three products, which is enough to verify ordering and deduplication. The 20-item history limit is covered by the backend integration test; testing that cap manually requires at least 21 distinct catalog products.

. Try dermatologist guidance

1. Sign out, then open **Dermatologist guidance** from Home. Confirm the general guidance cards load without signing in.
2. Check that a card shows its advice, source link, and the informational notice. Open **Read the source** and confirm it opens the cited source page.
3. Sign in as Account A. Open **Skin profile**, select **Dry**, save, and return to **Dermatologist guidance**. The screen requests guidance using the saved profile skin type.
4. Change the profile to **Oily**, save, and reopen the guidance screen. Confirm the returned guidance reflects the new preference.
5. Set the device or simulator language to French and reload the app. Confirm the guidance text and disclaimer are in French. You can also verify the API locale and explicit skin-type query from PowerShell:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/dermatologists/recommendations?skin_type=oily" -Headers @{"Accept-Language" = "fr"}
```

Valid skin types are `normal`, `dry`, `oily`, `combination`, and `sensitive`. The app screen uses the signed-in profile when one is saved; the query parameter is useful when checking another type directly.

Expected result: the screen remains informational, includes source attribution, and does not present the content as a diagnosis or personal medical advice.

. Create and share a routine

1 Prepare Account A's routine

1. Sign in as Account A and open **Account → Your routines**.
2. Choose **Morning** (or **Evening**) and choose **Add a step**.
3. Search for a demo product by name, select it, choose a step type, and choose **Add step**.
4. Add a second product if you want to check ordering. You can use **Earlier**, **Later**, and **Remove** from the routine screen.
5. Add a short private note to one step and save it. The note is used to verify that private notes are excluded from a shared routine.

Expected result: the chosen routine shows its ordered steps. The **Share this routine** control appears when the selected routine has at least one step.

2 Create a link and check its public view

1. On Account A's routine screen, select **Share this routine**.
2. Copy the link from the system share sheet. The app creates a link with a 7-day expiry by default.
3. Sign out, then open the copied link in the running app/development app. If using a physical phone, open it on a device that can reach the Expo server.
4. Confirm the public screen shows the routine slot, expiry date, step types, products, and available active ingredients. Confirm Account A's identity and the private note are not displayed.
5. Open a product from the shared view and return to the shared routine.

## 11. Stop the local stack

Stop the API with `Ctrl+C` in its terminal. Stop the local database from `backend/`:

```powershell
docker compose down
```

`docker compose down` keeps the local database volume. Only use `docker compose down -v` when you intentionally want to delete the local database and all of its test data.

