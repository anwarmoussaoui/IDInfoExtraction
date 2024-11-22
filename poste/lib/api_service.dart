import 'package:http/http.dart' as http;
import 'dart:convert';

import 'package:poste/model/post.dart';

// API base URL
const String baseUrl = "https://jsonplaceholder.typicode.com";

// Fetch all posts
Future<List<Post>> fetchPosts() async {
  final response = await http.get(Uri.parse("$baseUrl/posts"));

  if (response.statusCode == 200) {
    List<dynamic> data = json.decode(response.body);
    return data.map((json) => Post.fromJson(json)).toList();
  } else {
    throw Exception("Erreur lors de la récupération des posts");
  }
}

// Create a new post
Future<Post?> createPost(String title, String body) async {
  final response = await http.post(
    Uri.parse("$baseUrl/posts"),
    headers: {"Content-Type": "application/json"},
    body: json.encode({"title": title, "body": body}),
  );

  if (response.statusCode == 201) {
    return Post.fromJson(json.decode(response.body));
  } else {
    throw Exception("Erreur lors de la création du post");
  }
}

// Update an existing post
Future<void> updatePost(Post post) async {
  final response = await http.put(
    Uri.parse("$baseUrl/posts/${post.id}"),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode(post.toJson()),
  );

  if (response.statusCode != 200) {
    throw Exception("Erreur de mise à jour");
  }
}

// Delete a post
Future<void> deletePost(int id) async {
  final response = await http.delete(
    Uri.parse("$baseUrl/posts/$id"),
  );

  if (response.statusCode != 200) {
    throw Exception("Erreur de suppression");
  }
}
