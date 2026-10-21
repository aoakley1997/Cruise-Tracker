# Firestore rule addition for Poppy's postcard reactions

The website now stores each reaction in a separate document:
`/postcardReactions/{postcardId}`.

**Do not replace your existing Firestore rules with this snippet.**
Inside your existing `match /databases/{database}/documents { ... }` block,
add this match block alongside the existing `messages` match block:

```javascript
match /postcardReactions/{postcardId} {
  // Both Poppy and the adults can see her reactions.
  allow read: if request.auth != null;

  // Only a signed-in non-adult account can add/change a reaction.
  // This app's adult UID is explicitly excluded.
  allow create, update: if request.auth != null
    && request.auth.uid != "mim5JdqJnjO4WjYyDKFbooPfQbV2"
    && exists(/databases/$(database)/documents/messages/$(postcardId))
    && request.resource.data.keys().hasOnly(['emoji', 'byUid', 'updatedAt'])
    && request.resource.data.keys().hasAll(['emoji', 'byUid', 'updatedAt'])
    && request.resource.data.emoji in ['❤️', '🥰', '😂', '😘', '🚢', '🐒']
    && request.resource.data.byUid == request.auth.uid
    && request.resource.data.updatedAt == request.time
    && (resource == null || resource.data.byUid == request.auth.uid);

  allow delete: if false;
}
```

**Important:** This assumes Poppy is the only non-adult signed-in user.
For stricter security, replace the non-adult check with
`request.auth.uid == "POPPY_UID"` using her Firebase Authentication UID.

Deploy through Firebase Console > Firestore Database > Rules > Publish.
Existing `messages` rules must remain intact.
